import { useState } from 'react'

const KEY = 'sb-guide'

/** A short first-visit guide to the demo day. Closed once, it stays closed on this browser (spec 115). */
export function StartHere() {
  const [open, setOpen] = useState(() => { try { return localStorage.getItem(KEY) !== 'closed' } catch { return true } })
  if (!open) return null
  const close = () => { try { localStorage.setItem(KEY, 'closed') } catch { /* closes for this visit only */ } setOpen(false) }
  return (
    <section className="guide" aria-label="Start here">
      <div>
        <p className="eyebrow">Start here</p>
        <p>It is 10:30 at Main Street, a simulated dealership: 40 repair orders, 10 technicians, 10 bays. Reset the day any time from the top bar.</p>
        <ol>
          <li>RO-1013’s water pump gasket kit is out of stock and the car is due on the lift. Press <strong>See the options</strong> in the parts check below.</li>
          <li>Compare where the part can come from, press <strong>Show on the board</strong> to preview a plan, then approve one.</li>
          <li>Or type what a technician would say into the note box, for example “1013 no gasket kit”. Move the demo clock to see ordered parts come due.</li>
        </ol>
      </div>
      <button type="button" className="ghost" onClick={close}>Got it</button>
    </section>
  )
}
