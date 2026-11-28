import { useEffect, useState } from 'react'
import './roles.css'
import type { Day, Precheck, Proposal } from '../types'
import { answerRequest, checkLate, clock, confirmLate, getDay, getPrecheck, getProposal, orderPrecheck, replanLate, reportStall, wayBackText } from '../api'
import { ChasePanel } from '../ChasePanel'
import { IntakePanel } from '../IntakePanel'
import { OrderPanel } from '../OrderPanel'
import { PrecheckPanel } from '../PrecheckPanel'
import { StartHere } from '../StartHere'
import { usePoll } from '../usePoll'
import { RoleBar } from './RoleBar'

const message = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong')
const STATE = { requested: 'Requested', confirmed: 'Confirmed', received: 'Received' }

/** The parts counter's day: every ordered part, what its source said, and what can be ordered ahead (spec 116 rules 9 to 11). */
export function PartsView() {
  const [day, setDay] = useState<Day | null>(null)
  const [check, setCheck] = useState<Precheck | null>(null)
  const [pending, setPending] = useState<Proposal | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = async () => {
    const [d, c] = await Promise.all([getDay(), getPrecheck()])
    setDay(d); setCheck(c)
    setPending(d.open_proposal_id ? await getProposal(d.open_proposal_id) : null)
  }
  useEffect(() => { load().catch((e) => setError(message(e))) }, [])
  usePoll(() => { if (!busy) return load().catch(() => { /* the next round will try again */ }) })

  const run = async (work: () => Promise<void>) => {
    setBusy(true)
    try { await work(); setError(null) } catch (e) { setError(message(e)) } finally { setBusy(false) }
  }

  if (error && !day) return <main className="center"><p className="error" role="alert">Could not reach the StallBreaker API. ({error})</p></main>
  if (!day) return <main className="center"><p>Loading the day…</p></main>

  /** News the plan cannot absorb goes to the service manager as a proposal; no plan is shown here (rule 10). */
  const toManager = async (p: Proposal) => { setPending(p); await load(); setNotice(`Sent to the service manager: ${p.part_name} for ${p.ro_id} needs a new plan.`) }
  const answer = (roId: string, partId: string, what: 'confirmed' | 'received') => run(async () => {
    setDay(await answerRequest(roId, partId, what))
    setNotice(what === 'confirmed' ? `Recorded: the source confirmed the part for ${roId}.` : `Recorded: the part for ${roId} is here.`)
  })
  const late = (roId: string, partId: string, arrives: number) => run(async () => {
    const verdict = await checkLate(roId, partId, arrives)
    if (verdict.holds) { setDay(await confirmLate(roId, partId, arrives)); setNotice(`New time recorded for ${roId}: ${clock(arrives)}. The plan still holds.`) }
    else await toManager(await replanLate(roId, partId, { arrives_min: arrives }))
  })
  const otherSources = (roId: string, partId: string, cannotSupply: boolean) => run(async () => { await toManager(await replanLate(roId, partId, { cannot_supply: cannotSupply })) })
  const orderAhead = () => run(async () => { const r = await orderPrecheck(); setDay(r.day); setCheck(r.precheck); setNotice('Parts ordered ahead. The schedule did not change.') })

  const paused = pending ? `The service manager is still deciding ${pending.ro_id}. News that needs a new plan can be sent after that.` : null
  const rows = day.orders.filter((o) => o.status !== 'done').flatMap((o) => o.parts.filter((p) => p.request).map((p) => ({ o, p, r: p.request! })))
    .sort((a, b) => Number(!!b.r.chase) - Number(!!a.r.chase) || Number(a.r.state === 'received') - Number(b.r.state === 'received') || a.r.arrives_min - b.r.arrives_min)
  const selected = day.orders.find((o) => o.id === selectedId) ?? null

  return (
    <>
      <RoleBar role="parts" store={day.store.name}><span className="role-clock">{clock(day.now_min)}</span></RoleBar>
      <main className="role-main">
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice" role="status">{notice}</p>}
        <StartHere id="sb-guide-parts">
          <p>You run the parts counter at Main Street and it is {clock(day.now_min)}.</p>
          <ol>
            <li>The parts check below found jobs that will run short. Order the ones that can arrive in time.</li>
            <li>Each order then appears in the list as requested. When a source answers, press the button or paste the reply: “north confirmed the tensioner”.</li>
            <li>If a source cannot supply, it goes to the service manager for a new plan.</li>
          </ol>
        </StartHere>
        {paused && <p className="muted small paused">{paused}</p>}

        <ChasePanel day={day} onOpen={setSelectedId} />

        <IntakePanel busy={busy} label="What did the source say? Paste or type the reply." placeholder="For example: north confirmed the tensioner"
          accept={['confirmed', 'received', 'late_part', 'cannot_supply']} notYours="That is a technician’s report. It goes to the service manager from the technician’s screen."
          yes={{ cannot_supply: 'Yes, send to the service manager', late_part: 'Yes, check the plan' }}
          onAnswer={(ro, part, what) => { setSelectedId(ro); void answer(ro, part, what) }} onLate={(ro, part, t) => void late(ro, part, t)}
          onCannotSupply={(ro, part) => void otherSources(ro, part, true)} onMissing={() => undefined} />

        <div className="layout">
          <section className="orders-card" aria-label="Ordered parts">
            <h2 className="role-h">Ordered parts</h2>
            {rows.length === 0 ? <p className="muted">Nothing is on order. Parts ordered from the parts check or by an approved plan appear here.</p> : (
              <div className="table-scroll">
                <table className="orders-table">
                  <thead><tr><th scope="col">Job</th><th scope="col">Part</th><th scope="col">From</th><th scope="col">Due</th><th scope="col">State</th><th scope="col">Needed by</th><th scope="col">If it falls through</th><th scope="col"><span className="visually-hidden">Open</span></th></tr></thead>
                  <tbody>
                    {rows.map(({ o, p, r }) => (
                      <tr key={`${o.id}-${p.part_id}`} className={[r.chase ? 'chase' : '', selectedId === o.id ? 'picked' : ''].join(' ')}>
                        <th scope="row">{o.id}<small>{o.description}</small></th>
                        <td>{p.name}</td>
                        <td>{r.source_name}</td>
                        <td className="mono">{clock(r.arrives_min)}</td>
                        <td><span className={`badge ${r.state === 'requested' ? 'warn' : 'ok'}`}>{STATE[r.state]}</span>{r.chase && <small className="chase-text">{r.chase === 'no_answer' ? 'No answer yet' : 'Should be here'}</small>}</td>
                        <td className="mono">{clock(r.needed_by_min)}</td>
                        <td><small>{r.state === 'received' ? 'It is here.' : o.status === 'in_progress' ? 'The job is under way without it.' : wayBackText(r, r.source_name, day.now_min)}</small></td>
                        <td><button type="button" className="link" onClick={() => setSelectedId(o.id)}>Open</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
          <OrderPanel order={selected} busy={busy} canReport={!pending} now={day.now_min}
            onReport={(ro, part) => void run(async () => { await toManager(await reportStall(ro, part)) })}
            onAnswer={(ro, part, what) => void answer(ro, part, what)}
            onOtherSources={(ro, part, cannot) => void otherSources(ro, part, cannot)}
            onLateConfirm={(ro, part, t) => void run(async () => { setDay(await confirmLate(ro, part, t)); setNotice(`New time recorded for ${ro}. The plan did not change.`) })}
            onLateReplan={(p) => void toManager(p)} />
        </div>

        {check && <PrecheckPanel check={check} busy={busy} canDecide={false} onOrder={() => void orderAhead()} onDecide={() => undefined} />}
      </main>
    </>
  )
}
