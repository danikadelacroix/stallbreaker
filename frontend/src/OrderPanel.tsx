import { useEffect, useState } from 'react'
import type { LateCheck, Order, PartNeed, Proposal } from './types'
import { checkLate, clock, replanLate } from './api'

const STATUS_LABEL: Record<Order['status'], string> = {
  done: 'Done', in_progress: 'In progress', scheduled: 'Scheduled', waiting_for_part: 'Waiting for a part', unplanned: 'Not planned',
}
const SHORT_TEXT = { out_of_stock: 'Not in stock here', claimed_by_earlier_jobs: 'Earlier jobs will use the stock' }

interface LateProps { order: Order; part: PartNeed; busy: boolean; onConfirm: (arrives: number) => void; onReplan: (p: Proposal) => void }

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** Move a part's arrival time and see at once whether the plan can absorb it. */
function LateControl({ order, part, busy, onConfirm, onReplan }: LateProps) {
  const original = part.arrives_min!
  const [arrives, setArrives] = useState(original)
  const [result, setResult] = useState<{ at: number; check: LateCheck } | null>(null)
  const [problem, setProblem] = useState<string | null>(null)

  const [opening, setOpening] = useState(false)

  // Ask the engine shortly after the slider stops moving. Asking saves nothing.
  useEffect(() => {
    if (arrives === original) return
    let alive = true
    const timer = setTimeout(() => {
      checkLate(order.id, part.part_id, arrives)
        .then((check) => { if (alive) { setResult({ at: arrives, check }); setProblem(null) } })
        .catch((e: unknown) => { if (alive) setProblem(e instanceof Error ? e.message : 'Could not check the plan') })
    }, 250)
    return () => { alive = false; clearTimeout(timer) }
  }, [arrives, original, order.id, part.part_id])

  const verdict = arrives !== original && result && result.at === arrives ? result.check : null
  return (
    <div className="late">
      <label htmlFor={`late-${part.part_id}`}>New arrival time <strong>{clock(arrives)}</strong></label>
      <input id={`late-${part.part_id}`} type="range" min={original} max={original + 240} step={15} value={arrives} disabled={busy}
        onChange={(e) => setArrives(Number(e.target.value))} />
      {problem && <p className="verdict bad" role="alert">{problem}</p>}
      {arrives === original && <p className="verdict muted">Drag to see what a delay would do to the plan.</p>}
      {arrives !== original && !verdict && !problem && <p className="verdict muted">Checking the plan…</p>}
      {verdict?.holds && (
        <>
          <p className="verdict good" role="status">The plan holds. The job {order.status === 'waiting_for_part' ? 'resumes' : 'starts'} at {clock(verdict.starts_min)}, {verdict.spare_min} min after the part arrives.</p>
          <button type="button" className="ghost" disabled={busy} onClick={() => onConfirm(arrives)}>Record the new time</button>
        </>
      )}
      {verdict && !verdict.holds && (
        <>
          <p className="verdict bad" role="status">
            The plan no longer holds: the job was due to {order.status === 'waiting_for_part' ? 'resume' : 'start'} at {clock(order.start_min!)}.
            The best new plan: {plural(verdict.missed_promises, 'promise')} missed, {plural(verdict.jobs_moved, 'job')} moved.
          </p>
          <button type="button" className="primary" disabled={busy || opening} onClick={() => {
            setOpening(true)
            replanLate(order.id, part.part_id, arrives)
              .then(onReplan)
              .catch((e: unknown) => setProblem(e instanceof Error ? e.message : 'Could not open the new plan'))
              .finally(() => setOpening(false))
          }}>{opening ? 'Opening…' : 'See the new plan'}</button>
        </>
      )}
    </div>
  )
}

interface Props {
  order: Order | null; busy: boolean; canReport: boolean
  onReport: (roId: string, partId: string) => void
  onLateConfirm: (roId: string, partId: string, arrives: number) => void
  onLateReplan: (p: Proposal) => void
}

/** Details of the repair order picked on the board, with a way to report a part missing or running late. */
export function OrderPanel({ order, busy, canReport, onReport, onLateConfirm, onLateReplan }: Props) {
  const [lateFor, setLateFor] = useState<string | null>(null)
  if (!order) {
    return (
      <aside className="panel empty">
        <h2>Repair order</h2>
        <p>Pick a job on the board to see its technician, promise time and parts. From there you can report a part as missing.</p>
      </aside>
    )
  }
  const slack = order.end_min !== null ? order.promise_min - order.end_min : null
  const open = order.status === 'in_progress' || order.status === 'scheduled'
  const lateKey = (p: PartNeed) => `${order.id}:${p.part_id}:${p.arrives_min}`
  return (
    <aside className="panel">
      <p className="eyebrow">{order.id} · {STATUS_LABEL[order.status]}</p>
      <h2>{order.description}</h2>
      <p className="vehicle">{order.vehicle}</p>
      <dl>
        <div><dt>Technician</dt><dd>{order.technician ?? '—'}</dd></div>
        <div><dt>Bay</dt><dd>{order.bay ?? '—'}</dd></div>
        <div><dt>{order.status === 'waiting_for_part' ? 'Resumes' : 'Planned'}</dt><dd>{order.start_min !== null ? `${clock(order.start_min)} to ${clock(order.end_min!)}` : '—'}</dd></div>
        <div><dt>Promised</dt><dd>{clock(order.promise_min)}</dd></div>
        <div>
          <dt>Margin</dt>
          <dd className={slack !== null && slack < 0 ? 'bad' : ''}>
            {slack === null ? '—' : slack >= 0 ? `${slack} min before the promise` : `${-slack} min after the promise`}
          </dd>
        </div>
      </dl>
      <h3>Parts needed</h3>
      {order.parts.length === 0 ? <p className="muted">No parts for this job.</p> : (
        <ul className="parts">
          {order.parts.map((p) => {
            const onItsWay = !!p.sourced_from && order.status !== 'done' && order.status !== 'in_progress'
            return (
              <li key={p.part_id} className={p.shortfall ? 'short' : ''}>
                <div className="part-line">
                  <div>
                    <span>{p.name}</span>
                    <span className="stock">
                      {p.sourced_from ? `Arriving ${clock(p.arrives_min!)} from ${p.sourced_from}` : p.shortfall ? SHORT_TEXT[p.shortfall] : `${p.on_hand_home} in stock`}
                    </span>
                  </div>
                  {open && !p.sourced_from && (
                    <button type="button" className="link" disabled={busy || !canReport} onClick={() => onReport(order.id, p.part_id)}>Report missing</button>
                  )}
                  {onItsWay && canReport && (
                    <button type="button" className="link" disabled={busy} aria-expanded={lateFor === lateKey(p)}
                      onClick={() => setLateFor(lateFor === lateKey(p) ? null : lateKey(p))}>
                      {lateFor === lateKey(p) ? 'Close' : 'Running late?'}
                    </button>
                  )}
                </div>
                {onItsWay && canReport && lateFor === lateKey(p) && (
                  <LateControl key={lateKey(p)} order={order} part={p} busy={busy}
                    onConfirm={(t) => { setLateFor(null); onLateConfirm(order.id, p.part_id, t) }}
                    onReplan={(proposal) => { setLateFor(null); onLateReplan(proposal) }} />
                )}
              </li>
            )
          })}
        </ul>
      )}
      {open && order.parts.length > 0 && !canReport && <p className="muted small">Decide the open stall first.</p>}
    </aside>
  )
}
