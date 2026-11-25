import type { Day } from './types'
import { clock, wayBackText } from './api'

/** Ordered parts that someone should chase now: the source has not answered in time, or the part should be here and is not. */
export function ChasePanel({ day, onOpen }: { day: Day; onOpen: (roId: string) => void }) {
  const items = day.orders.flatMap((o) => o.parts.filter((p) => p.request?.chase).map((p) => ({ order: o, part: p, req: p.request! })))
  if (items.length === 0) return null
  return (
    <section className="chase-panel" aria-label="Ordered parts to chase">
      <p className="eyebrow alert">Ordered parts to chase · {clock(day.now_min)}</p>
      <ul>
        {items.map(({ order, part, req }) => (
          <li key={`${order.id}-${part.part_id}`}>
            <p>
              <strong>{order.id}</strong> · {part.name} from {req.source_name}, due {clock(req.arrives_min)}:{' '}
              {req.chase === 'no_answer' ? 'not confirmed yet.' : 'it should be here by now.'}{' '}
              <span className="muted">{order.status === 'in_progress' ? 'The job is under way without it.' : wayBackText(req, req.source_name, day.now_min)}</span>
            </p>
            <button type="button" className="link" onClick={() => onOpen(order.id)}>Open the job</button>
          </li>
        ))}
      </ul>
    </section>
  )
}
