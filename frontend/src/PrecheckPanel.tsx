import type { Precheck } from './types'
import { clock } from './api'

interface Props { check: Precheck; busy: boolean; onOrder: () => void; onDecide: (roId: string, partId: string) => void
  /** False for a role that does not decide plans: shortfalls that need a decision are shown as waiting for the manager. */
  canDecide?: boolean }

const WHY = { out_of_stock: 'none on the shelf', claimed_by_earlier_jobs: 'earlier jobs will use the stock' }

/** The parts check: jobs that will run short of a part, found before anyone takes the car apart. */
export function PrecheckPanel({ check, busy, onOrder, onDecide, canDecide = true }: Props) {
  if (check.flagged.length === 0) return null
  const n = check.flagged.length
  return (
    <section className="precheck" aria-label="Parts check">
      <header>
        <div>
          <p className="eyebrow">Parts check · {clock(check.checked_at_min)}</p>
          <h2>{n} {n === 1 ? 'job' : 'jobs'} will be short of a part</h2>
          <p className="muted">The {check.jobs_checked} open jobs were checked against the shelf, in the order they start.</p>
        </div>
        {check.fixable_without_replan > 0 && (
          <button type="button" className="primary" disabled={busy} onClick={onOrder}>
            Order the {check.fixable_without_replan} that can arrive in time (${Math.round(check.fix_cost)})
          </button>
        )}
      </header>
      <div className="table-scroll">
        <table>
          <thead>
            <tr><th scope="col">Job</th><th scope="col">Starts</th><th scope="col">Part</th><th scope="col">What can be done</th><th scope="col"><span className="visually-hidden">Action</span></th></tr>
          </thead>
          <tbody>
            {check.flagged.map((f) => (
              <tr key={`${f.ro_id}-${f.part_id}`}>
                <th scope="row">{f.ro_id}<small>{f.description}</small></th>
                <td>{clock(f.start_min)}</td>
                <td>{f.part_name}<small>{WHY[f.reason]}</small></td>
                <td>
                  {f.fix ? (
                    <><span className="badge ok">No re-plan needed</span> {f.fix.source_name} can deliver by {clock(f.fix.arrives_min)}, ${Math.round(f.fix.cost)}</>
                  ) : f.already_started ? (
                    <><span className="badge warn">Decide now</span> the car is already in the bay</>
                  ) : (
                    <><span className="badge warn">Needs a re-plan</span> no safe source arrives before it starts</>
                  )}
                </td>
                <td>{!f.fix && (canDecide
                  ? <button type="button" className="link" disabled={busy} onClick={() => onDecide(f.ro_id, f.part_id)}>See the options</button>
                  : <span className="muted small">For the service manager</span>)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
