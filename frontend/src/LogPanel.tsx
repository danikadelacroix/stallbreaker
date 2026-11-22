import type { LogEntry } from './types'
import { clock } from './api'

const money = (n: unknown) => (typeof n === 'number' ? `$${Math.round(n)}` : '')

/** What has been decided today, newest first. */
export function LogPanel({ entries }: { entries: LogEntry[] }) {
  return (
    <section className="log" aria-label="Decision log">
      <h2>Decision log</h2>
      <ol>
        {entries.map((e) => {
          const d = e.detail
          if (e.kind === 'parts_ordered_ahead') {
            const orders = (d.orders ?? []) as { ro_id: string; part: string; source: string; arrives_min: number; job_starts_min: number }[]
            return (
              <li key={e.id}>
                <p><time>{clock(e.at_min)}</time> Parts check: {orders.length} {orders.length === 1 ? 'part' : 'parts'} ordered ahead ({money(d.total_cost)}). The schedule did not change.</p>
                <ul className="sub">
                  {orders.map((o) => <li key={`${o.ro_id}-${o.part}`}><strong>{o.ro_id}</strong> {o.part} from {o.source}, arriving {clock(o.arrives_min)} (job starts {clock(o.job_starts_min)})</li>)}
                </ul>
              </li>
            )
          }
          if (e.kind === 'part_late_plan_holds') {
            return (
              <li key={e.id}>
                <p><time>{clock(e.at_min)}</time> <strong>{String(d.ro_id)}</strong>: {String(d.part)} now arriving {clock(Number(d.arrives_min))}, not {clock(Number(d.old_arrives_min))}. The plan holds with {String(d.spare_min)} min to spare.</p>
              </li>
            )
          }
          if (e.kind === 'stall_resolved' || e.kind === 'part_late_replanned') {
            const moved = Array.isArray(d.jobs_moved) ? (d.jobs_moved as string[]) : []
            return (
              <li key={e.id}>
                <p>
                  <time>{clock(e.at_min)}</time> <strong>{String(d.ro_id)}</strong>: {e.kind === 'part_late_replanned'
                    ? `${String(d.part)} now arriving ${clock(Number(d.arrives_min))}, not ${clock(Number(d.old_arrives_min))}.`
                    : `${String(d.part)} sourced from ${String(d.source)} (${money(d.cost)}), arriving ${clock(Number(d.arrives_min))}.`}
                  Plan approved ({String(d.option).toLowerCase()}): {Number(d.missed_promises) === 1 ? '1 promise missed' : `${String(d.missed_promises)} promises missed`}, {moved.length ? `moved ${moved.join(', ')}` : 'no other job moved'}.
                </p>
                {(d.customer_messages ?? []).map((m) => (
                  <blockquote key={m.ro_id}>
                    <span className="msg-label">Draft message to the customer of {m.ro_id}</span>
                    {m.text}
                  </blockquote>
                ))}
                {(d.customer_messages ?? []).length > 0 && <p className="muted small">Written by: {String(d.messages_written_by)}</p>}
              </li>
            )
          }
          return (
            <li key={e.id}>
              <p><time>{clock(e.at_min)}</time> Morning plan built by the {String(d.built_by)}: {String(d.orders)} repair orders, {String(d.missed_promises)} promises missed.</p>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
