import { useEffect, useState } from 'react'
import type { Day, LogEntry, Order, PlanOption, Precheck, Proposal, Segment } from './types'
import { approveProposal, clock, confirmLate, dismissProposal, getDay, getLog, getPrecheck, getProposal, orderPrecheck, reportStall, resetDay, setClock } from './api'
import { Board } from './Board'
import { OrderPanel } from './OrderPanel'
import { StallCard } from './StallCard'
import { LogPanel } from './LogPanel'
import { PrecheckPanel } from './PrecheckPanel'

const message = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong')

/** While a stall is open, the board shows the plan being previewed instead of the live one. */
function buildView(day: Day | null, proposal: Proposal | null, option: PlanOption | null): { orders: Order[]; segments: Segment[]; moved?: Set<string> } {
  if (!day) return { orders: [], segments: [] }
  if (!proposal || !option) return { orders: day.orders, segments: day.segments }
  const orders = day.orders.map((o): Order => {
    const a = option.assignments[o.id]
    if (!a) return o
    const waiting = o.id === proposal.ro_id && proposal.in_progress
    return { ...o, start_min: a.start_min, end_min: a.end_min, technician: a.technician, bay: a.bay, late: a.end_min > o.promise_min,
      status: waiting ? 'waiting_for_part' : o.status, short_of_parts: o.id === proposal.ro_id ? false : o.short_of_parts }
  })
  const stalled = proposal.current
  const extra: Segment[] = proposal.in_progress ? [
    { ro_id: proposal.ro_id, kind: 'done', start_min: stalled.start_min, end_min: proposal.now_min, technician: stalled.technician, bay: stalled.bay },
    { ro_id: proposal.ro_id, kind: 'hold', start_min: proposal.now_min, end_min: option.stalled_job.start_min, technician: null, bay: stalled.bay },
  ] : []
  return { orders, segments: [...day.segments, ...extra.filter((s) => s.end_min > s.start_min)], moved: new Set(option.changes.map((c) => c.ro_id)) }
}

export default function App() {
  const [day, setDay] = useState<Day | null>(null)
  const [log, setLog] = useState<LogEntry[]>([])
  const [check, setCheck] = useState<Precheck | null>(null)
  const [proposal, setProposal] = useState<Proposal | null>(null)
  const [previewKey, setPreviewKey] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  /** Run one action against the API, showing its error if it fails. */
  const run = async (work: () => Promise<void>) => {
    setBusy(true)
    try { await work(); setError(null) }
    catch (e) { setError(message(e)) }
    finally { setBusy(false) }
  }

  // First load: the day, the log, and any stall still waiting for a decision (so a refresh loses nothing).
  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [d, l, c] = await Promise.all([getDay(), getLog(), getPrecheck()])
        const p = d.open_proposal_id ? await getProposal(d.open_proposal_id) : null
        if (!alive) return
        setDay(d); setLog(l); setCheck(c); setProposal(p); setPreviewKey(p?.options[0]?.key ?? '')
        if (p) setSelectedId(p.ro_id)
      } catch (e) { if (alive) setError(message(e)) }
    })()
    return () => { alive = false }
  }, [])

  const option = proposal ? proposal.options.find((o) => o.key === previewKey) ?? proposal.options[0] : null

  const view = buildView(day, proposal, option)

  if (error && !day) return <main className="center"><p className="error" role="alert">Could not reach the StallBreaker API. Is it running on port 8000? ({error})</p></main>
  if (!day) return <main className="center"><p>Loading the day…</p></main>

  const selected = view.orders.find((o) => o.id === selectedId) ?? null
  const s = day.summary
  const flagged = day.orders.filter((o) => o.short_of_parts && o.status !== 'done').length

  const openStall = (roId: string, partId: string, force: string | null = null) => run(async () => {
    const p = await reportStall(roId, partId, force)
    setProposal(p); setPreviewKey(p.options[0].key); setSelectedId(p.ro_id); setNotice(null)
  })
  /** The log and the parts check both change whenever the plan or the stock does. */
  const refreshSide = async () => { const [l, c] = await Promise.all([getLog(), getPrecheck()]); setLog(l); setCheck(c) }
  const approve = (key: string) => run(async () => {
    if (!proposal) return
    const chosen = proposal.options.find((o) => o.key === key)
    setDay(await approveProposal(proposal.id, key))
    await refreshSide()
    setNotice(proposal.kind === 'late_part'
      ? `New plan approved for ${proposal.ro_id} after the late part. The decision is in the log below.`
      : `Plan approved for ${proposal.ro_id}: ${proposal.part_name} from ${chosen?.source_name}. The decision is in the log below.`)
    setProposal(null)
  })
  const dismiss = () => run(async () => {
    if (!proposal) return
    setDay(await dismissProposal(proposal.id)); setProposal(null)
  })
  const orderAhead = () => run(async () => {
    const r = await orderPrecheck()
    setDay(r.day); await refreshSide()
    setNotice('Parts ordered ahead. The schedule did not change; the orders are in the log below.')
  })
  const lateConfirm = (roId: string, partId: string, arrives: number) => run(async () => {
    setDay(await confirmLate(roId, partId, arrives)); await refreshSide()
    setNotice(`New arrival time recorded for ${roId}. The plan did not change.`)
  })
  const lateReplan = (p: Proposal) => { setProposal(p); setPreviewKey(p.options[0].key); setSelectedId(p.ro_id); setNotice(null) }

  return (
    <>
      <header className="top">
        <div className="brand">
          <h1>StallBreaker</h1>
          <p>{day.store.name} · service schedule · simulated data</p>
        </div>
        <div className="clock">
          <label htmlFor="clock">Demo clock <strong>{clock(day.now_min)}</strong></label>
          <input
            id="clock" type="range" min={0} max={day.horizon_min} step={15} value={day.now_min} disabled={busy || !!proposal}
            onChange={(e) => void run(async () => { setDay(await setClock(Number(e.target.value))); await refreshSide() })}
          />
          <button type="button" disabled={busy} onClick={() => void run(async () => {
            setDay(await resetDay()); await refreshSide(); setProposal(null); setSelectedId(null); setNotice(null)
          })}>
            {busy ? 'Working…' : 'Reset day'}
          </button>
        </div>
      </header>
      <main>
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice" role="status">{notice}</p>}
        <ul className="stats" aria-label="Today at a glance">
          <li><strong>{s.orders}</strong><span>repair orders</span></li>
          <li><strong>{s.done}</strong><span>done</span></li>
          <li><strong>{s.in_progress}</strong><span>in progress</span></li>
          <li><strong>{s.scheduled}</strong><span>still to start</span></li>
          <li className={s.promises_at_risk ? 'warn' : 'good'}><strong>{s.promises_at_risk}</strong><span>promises missed</span></li>
          <li className={flagged ? 'warn' : 'good'}><strong>{flagged}</strong><span>jobs missing a part</span></li>
        </ul>
        {!proposal && check && <PrecheckPanel check={check} busy={busy} onOrder={() => void orderAhead()} onDecide={(ro, part) => void openStall(ro, part)} />}
        {proposal && (
          <StallCard
            proposal={proposal} previewKey={option!.key} busy={busy}
            onPreview={setPreviewKey}
            onForce={(src) => { if (proposal.kind === 'missing_part') void openStall(proposal.ro_id, proposal.part_id, src) }}
            onApprove={(key) => void approve(key)}
            onDismiss={() => void dismiss()}
          />
        )}
        <div className="layout">
          <Board day={day} orders={view.orders} segments={view.segments} selectedId={selectedId} onSelect={setSelectedId}
            moved={view.moved} preview={proposal && option ? option.title : null} />
          <OrderPanel order={selected} busy={busy} canReport={!proposal} onReport={(ro, part) => void openStall(ro, part)}
            onLateConfirm={(ro, part, t) => void lateConfirm(ro, part, t)} onLateReplan={lateReplan} />
        </div>
        <LogPanel entries={log} />
      </main>
    </>
  )
}
