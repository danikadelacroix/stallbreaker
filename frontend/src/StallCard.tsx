import type { PlanOption, Proposal } from './types'
import { clock, span } from './api'

interface Props {
  proposal: Proposal
  previewKey: string
  busy: boolean
  onPreview: (key: string) => void
  onForce: (sourceId: string | null) => void
  /** Keep the car in its bay, roll it out, or (null) let the engine decide. */
  onBay: (bay: 'hold' | 'roll_out' | null) => void
  onApprove: (key: string) => void
  onDismiss: () => void
}

const pctText = (r: number | null) => (r === null ? '—' : `${Math.round(r * 100)}%`)
const money = (n: number) => `$${Math.round(n)}`
const slack = (min: number, capped: boolean) => (capped ? `over ${span(min)}` : span(min))

/** One sentence on how much delay of the part the plan can take. */
function marginText(o: PlanOption, roId: string): string {
  const selfLate = o.late_orders.some((l) => l.ro_id === roId)
  const own = selfLate ? `${roId} gets later with any delay. ` : ''
  const further = o.missed_promises ? 'further ' : ''
  if (o.late_margin_min === 0) return `${own}No slack: a part 15 min late costs another promise.`
  if (o.late_margin_capped) return `${own}No ${further}promise is lost even if the part is ${span(o.late_margin_min)} late.`
  return `${own}No ${further}promise is lost if the part is up to ${span(o.late_margin_min)} late.`
}

interface OptionProps {
  o: PlanOption; roId: string; title: string; chosen: boolean; busy: boolean
  /** What the manager may switch the bay decision to, if anything. */
  bayChoice: { label: string; onClick: () => void } | null
  onPreview: () => void; onApprove: () => void
}

function Option({ o, roId, title, chosen, busy, bayChoice, onPreview, onApprove }: OptionProps) {
  return (
    <article className={`option ${chosen ? 'chosen' : ''}`}>
      <header>
        <h3>{title}</h3>
        <span className={`badge ${o.proven_best ? 'ok' : 'warn'}`}>
          {o.proven_best ? `Proven best in ${o.solve_seconds.toFixed(2)} s` : 'Best found within the time limit'}
        </span>
      </header>
      <p className="via">Part from <strong>{o.source_name}</strong>, arriving {clock(o.arrives_min)}, {money(o.cost)}</p>
      <ul className="metrics">
        <li className={o.missed_promises ? 'bad' : 'good'}><strong>{o.missed_promises}</strong><span>{o.missed_promises === 1 ? 'promise missed' : 'promises missed'}</span></li>
        <li><strong>{o.late_minutes}</strong><span>late minutes</span></li>
        <li><strong>{o.jobs_moved}</strong><span>jobs moved</span></li>
        <li><strong>{span(o.bay_blocked_min)}</strong><span>bay blocked</span></li>
      </ul>
      {o.changes.length > 0 && (
        <ul className="changes">
          {o.changes.map((c) => (
            <li key={c.ro_id}>
              <strong>{c.ro_id}</strong> {c.description}: {c.before.bay} {clock(c.before.start_min)} ({c.before.technician}) → {c.after.bay} {clock(c.after.start_min)} ({c.after.technician})
            </li>
          ))}
        </ul>
      )}
      {o.late_orders.filter((l) => !l.late_before).map((l) => (
        <p key={l.ro_id} className="late-note">{l.ro_id} would be ready at {clock(l.end_min)}, {span(l.end_min - l.promise_min)} after its promise.</p>
      ))}
      {o.bay_note && (
        <p className="bay-note">
          <strong>The bay:</strong> {o.bay_note}{' '}
          {bayChoice && <button type="button" className="link" disabled={busy} onClick={bayChoice.onClick}>{bayChoice.label}</button>}
        </p>
      )}
      <p className={`needs-you ${o.needs_you.length ? '' : 'clear'}`}>
        {o.needs_you.length ? <><strong>Needs you because</strong> {o.needs_you.join('; ')}.</> : <strong>Nothing is traded off in this plan.</strong>}
      </p>
      <p className={`margin-note ${o.late_margin_min === 0 ? 'tight' : ''}`}><strong>If the part is late:</strong> {marginText(o, roId)}</p>
      <div className="actions">
        <button type="button" className="ghost" onClick={onPreview} aria-pressed={chosen} disabled={chosen}>{chosen ? 'Shown on the board' : 'Show on the board'}</button>
        <button type="button" className="primary" onClick={onApprove} disabled={busy}>Approve this plan</button>
      </div>
    </article>
  )
}

/** One stall: where the part could come from, and the plans the engine offers. */
export function StallCard({ proposal: p, previewKey, busy, onPreview, onForce, onBay, onApprove, onDismiss }: Props) {
  const shown = p.options.find((o) => o.key === previewKey) ?? p.options[0]
  const nr = p.no_replan
  const late = p.kind === 'late_part'
  return (
    <section className="stall" aria-label="Missing part">
      <header className="stall-head">
        <div>
          <p className="eyebrow alert">{late ? `Part running late · now due ${clock(p.new_arrives_min!)}, was ${clock(p.old_arrives_min!)}` : `Part missing · reported ${clock(p.now_min)}`}</p>
          <h2>{p.part_name}</h2>
          <p className="muted">
            {p.ro_id} · {p.description} · {p.vehicle} · {!p.in_progress ? 'work has not started, so no bay is blocked' : shown.bay_decision === 'roll_out' ? `car is in ${p.current.bay} and would be rolled out` : `car is already in ${p.current.bay}, so the bay stays blocked`}
          </p>
        </div>
        <button type="button" className="ghost" onClick={onDismiss} disabled={busy}>Close without deciding</button>
      </header>

      <div className="stall-body">
        <div className="sources">
          <h3>{late ? 'The part is already on its way' : 'Where the part can come from'}</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr><th scope="col">Source</th><th scope="col">Stock</th><th scope="col">Arrives</th><th scope="col">Cost</th><th scope="col">Shortage risk</th>{!late && <><th scope="col">The day with this source</th><th scope="col">Part can be late by</th></>}<th scope="col"><span className="visually-hidden">Choose</span></th></tr>
              </thead>
              <tbody>
                {p.sources.map((s) => {
                  const picked = shown.source_id === s.id
                  return (
                    <tr key={s.id} className={[picked ? 'picked' : '', !s.available ? 'off' : '', s.available && !s.safe ? 'unsafe' : ''].join(' ')}>
                      <th scope="row">
                        {s.name}
                        {picked && <span className="badge ok">Chosen</span>}
                        {!picked && !late && s.id === p.engine_source_id && <span className="badge ok">Engine's pick</span>}
                        {s.available && !s.safe && <span className="badge warn">Unsafe to lend</span>}
                      </th>
                      <td>{late ? 'ordered' : s.on_hand === null ? 'supplier' : s.available ? `${s.on_hand} on hand` : 'none to spare'}</td>
                      <td>{s.available ? clock(p.now_min + s.eta_min) : '—'}</td>
                      <td>{s.available ? money(s.cost) : '—'}</td>
                      <td title={s.risk_basis ?? undefined}>
                        {s.available ? pctText(s.risk) : '—'}
                        {s.available && s.risk_basis && s.kind === 'sister_store' && <small>{s.risk_basis}</small>}
                      </td>
                      {!late && (
                        <>
                          <td>
                            {s.outcome ? `${s.outcome.missed_promises === 1 ? '1 promise missed' : `${s.outcome.missed_promises} promises missed`}, ${s.outcome.late_minutes} late min` : '—'}
                            {s.outcome && <small>{s.why_not ?? "The engine's choice."}</small>}
                          </td>
                          <td className={s.outcome && s.outcome.late_margin_min === 0 ? 'tight' : ''}>{s.outcome ? slack(s.outcome.late_margin_min, s.outcome.late_margin_capped) : '—'}</td>
                        </>
                      )}
                      <td>
                        {!late && s.available && p.forced_source !== s.id && (
                          <button type="button" className="link" disabled={busy} onClick={() => onForce(s.id)}>Use this one</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {p.forced_source && (
            <p className="forced" role="status">
              You chose the source yourself. <button type="button" className="link" disabled={busy} onClick={() => onForce(null)}>Let the engine choose</button>
            </p>
          )}
          <p className="baseline">
            <strong>If nobody re-plans</strong> and the shop {late ? 'just waits' : `waits for ${nr.source_name}`} (arrives {clock(nr.arrives_min)}): {nr.missed_promises === 1 ? '1 promise missed' : `${nr.missed_promises} promises missed`}, {nr.late_minutes} late minutes{nr.bay_blocked_min ? `, bay blocked ${span(nr.bay_blocked_min)}` : ''}.
          </p>
        </div>
        <div className="options">
          {p.options.map((o) => (
            <Option key={o.key} o={o} roId={p.ro_id} title={p.forced_source && p.options.length === 1 ? 'Plan with the source you chose' : o.title} chosen={o.key === shown.key} busy={busy}
              bayChoice={late || !p.can_roll_out ? null
                : p.forced_bay ? { label: 'Let the engine decide', onClick: () => onBay(null) }
                : o.bay_decision === 'hold' ? { label: 'Roll it out anyway', onClick: () => onBay('roll_out') }
                : { label: 'Keep it in the bay', onClick: () => onBay('hold') }}
              onPreview={() => onPreview(o.key)} onApprove={() => onApprove(o.key)} />
          ))}
        </div>
      </div>
    </section>
  )
}
