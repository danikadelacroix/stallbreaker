import type { Day, Order, Segment } from './types'
import { clock } from './api'

interface Props {
  day: Day
  /** Orders to draw. In a preview these carry the proposed times, not the live ones. */
  orders: Order[]
  segments: Segment[]
  selectedId: string | null
  onSelect: (id: string) => void
  /** Jobs that a previewed plan would move. */
  moved?: Set<string>
  preview?: string | null
}

/** The schedule board: one row per bay, one bar per repair order, time running left to right. */
export function Board({ day, orders, segments, selectedId, onSelect, moved, preview }: Props) {
  const H = day.horizon_min
  const pct = (min: number) => `${(Math.min(min, H) / H) * 100}%`
  const ticks = Array.from({ length: H / 60 + 1 }, (_, i) => i * 60)
  const byBay = new Map<string, Order[]>()
  for (const o of orders) if (o.bay) byBay.set(o.bay, [...(byBay.get(o.bay) ?? []), o])
  const selected = orders.find((o) => o.id === selectedId) ?? null

  return (
    <section className={`board ${preview ? 'previewing' : ''}`} aria-label="Schedule board">
      {preview && <p className="preview-note" role="status">Preview: <strong>{preview}</strong>. Nothing changes until a plan is approved.</p>}
      <div className="board-scroll">
        <div className="board-grid">
          <div className="axis">
            <div className="row-label" />
            <div className="track axis-track">
              {ticks.map((t) => (
                <span key={t} className="tick" style={{ left: pct(t) }}>{clock(t)}</span>
              ))}
            </div>
          </div>
          {day.bays.map((bay) => (
            <div className="row" key={bay.id}>
              <div className="row-label">
                <strong>{bay.name}</strong>
                <span>{bay.kind}</span>
              </div>
              <div className="track">
                {ticks.map((t) => <span key={t} className="gridline" style={{ left: pct(t) }} />)}
                {segments.filter((s) => s.bay === bay.id).map((s) => {
                  const width = ((Math.min(s.end_min, H) - s.start_min) / H) * 100
                  return s.kind === 'hold' ? (
                    <span key={`${s.ro_id}-hold`} className="hold" style={{ left: pct(s.start_min), width: `calc(${width}% - 3px)` }} title={`${s.ro_id}: bay blocked, waiting for the part`}>
                      {width > 7 && 'waiting for part'}
                    </span>
                  ) : (
                    <span key={`${s.ro_id}-done`} className="bar done ghost" style={{ left: pct(s.start_min), width: `calc(${width}% - 3px)` }} title={`${s.ro_id}: work done before the stall`}>
                      {width > 3 && <span className="bar-id">{s.ro_id.replace('RO-', '')}</span>}
                    </span>
                  )
                })}
                {(byBay.get(bay.id) ?? []).map((o) => {
                  const width = ((Math.min(o.end_min!, H) - o.start_min!) / H) * 100
                  const cls = ['bar', o.status, o.late ? 'late' : '', o.short_of_parts && o.status !== 'done' ? 'short' : '',
                    moved?.has(o.id) ? 'moved' : '', o.id === selectedId ? 'selected' : ''].join(' ')
                  return (
                    <button
                      key={o.id} type="button" className={cls}
                      style={{ left: pct(o.start_min!), width: `calc(${width}% - 3px)` }}
                      onClick={() => onSelect(o.id)}
                      aria-pressed={o.id === selectedId}
                      aria-label={`${o.id}, ${o.description}, ${clock(o.start_min!)} to ${clock(o.end_min!)}, ${o.technician}${o.late ? ', misses its promise' : ''}${moved?.has(o.id) ? ', moved in this plan' : ''}`}
                      title={`${o.id} · ${o.description} · ${o.technician}`}
                    >
                      <span className="bar-id">{o.id.replace('RO-', '')}</span>
                      {width > 9 && <span className="bar-text">{o.description}</span>}
                    </button>
                  )
                })}
                {selected && selected.bay === bay.id && (
                  <span className="promise" style={{ left: pct(selected.promise_min) }} title={`Promised ${clock(selected.promise_min)}`} />
                )}
              </div>
            </div>
          ))}
          <div className="now" style={{ left: `calc(var(--label-w) + (100% - var(--label-w)) * ${day.now_min / H})` }}>
            <span>{clock(day.now_min)}</span>
          </div>
        </div>
      </div>
      <ul className="legend" aria-label="Legend">
        <li><i className="sw done" />Done</li>
        <li><i className="sw in_progress" />In progress</li>
        <li><i className="sw scheduled" />Scheduled</li>
        <li><i className="sw short" />Part not in stock</li>
        <li><i className="sw hold-sw" />Bay blocked, waiting for a part</li>
        <li><i className="sw late-sw" />Misses its promise</li>
        {moved && <li><i className="sw moved-sw" />Moved in this plan</li>}
      </ul>
    </section>
  )
}
