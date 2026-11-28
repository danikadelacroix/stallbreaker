import './landing.css'
import { Logo } from './Logo'
import { ThemeToggle } from './theme'

const Icon = ({ d }: { d: string }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={d} /></svg>
)
const ICONS = {
  manager: 'M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 3h6v4H9zM9 14l2 2 4-4',
  technician: 'M7 10h3V7L6.5 3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1-3 3l-6-6a6 6 0 0 1-8-8L7 10',
  parts: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3M12 12l8-4.5M12 12v9M12 12L4 7.5',
}

const STEPS = [
  { title: 'Report it', text: 'The technician says what is wrong in their own words. StallBreaker reads it into a job and a part, quotes the words it relied on, and opens nothing until someone confirms.',
    example: '“1013 wp off, gskt kit in bin is for the 2.0 not 2.5t”' },
  { title: 'Find every source', text: 'Sister stores, the local vendor and the OEM depot, each with arrival time and cost. A sister store is marked unsafe to borrow from when lending would likely leave it short, judged from 51 months of real part demand.',
    example: '4 sources compared · 1 unsafe to lend' },
  { title: 'Re-plan the day', text: 'One optimisation chooses the source and moves the other jobs at the same time, so the fewest customer promises are missed. Every plan is checked against the shop’s rules and proven best, usually in under a second.',
    example: 'Proven best in 0.08 s' },
  { title: 'Approve and follow up', text: 'The service manager approves one plan. The parts counter then tracks the order from requested to confirmed to received, and sees the last moment to switch to a backup source.',
    example: 'Switch to the local vendor by 11:15 if North goes quiet' },
]

const ROLES = [
  { icon: ICONS.manager, who: 'Service manager', verb: 'Decides', text: 'Sees the recommended plan, what it trades off, and what waiting would cost. Nothing is ordered or moved without their approval.' },
  { icon: ICONS.technician, who: 'Technician', verb: 'Reports', text: 'Types or dictates what is missing, the way they would tell a colleague, and gets back to the next job.' },
  { icon: ICONS.parts, who: 'Parts counter', verb: 'Follows up', text: 'Sees every ordered part as requested, confirmed or received, records what the source said, and knows when to chase.' },
]

const WHY = [
  { title: 'Proven best, not a rule of thumb', text: 'A constraint solver plans the part source and the schedule together. Every plan says whether it is proven best and how long that took.' },
  { title: 'Shows its working', text: 'For every source it did not pick, you see what the day would look like with it and the one reason it lost.' },
  { title: 'Knows how much room there is', text: 'Each plan says how late the part can be before another promise is lost, and when to switch if the source goes quiet.' },
  { title: 'A person stays in charge', text: 'Reading a note saves nothing, every plan waits for approval, and the app never contacts a supplier on its own.' },
]

const NUMBERS = [
  { value: '2 → 1', label: 'promises missed on the first stall of the day, without and with a re-plan' },
  { value: '375 → 30', label: 'late minutes on the same stall' },
  { value: '< 1 s', label: 'to a plan that is proven best' },
  { value: '77', label: 'automated checks behind the rules' },
]

/** A still of the decision the demo shows for the first stall, with the demo day's real numbers. */
function Preview() {
  return (
    <figure className="lp-preview">
      <div className="lp-preview-card">
        <p className="lp-preview-eyebrow">Part missing · reported 10:30</p>
        <p className="lp-preview-title">Water pump gasket kit for RO-1013</p>
        <p className="lp-preview-sub">2020 Ford Explorer · Bay 7 · the car is due on the lift now</p>
        <div className="lp-preview-plan">
          <p className="lp-preview-rec">Recommended: <strong>Local vendor</strong>, here at 11:30, $85</p>
          <ul>
            <li><strong>1</strong><span>promise missed, not 2</span></li>
            <li><strong>30 min</strong><span>late, not 375</span></li>
            <li><strong>0.08 s</strong><span>to prove it best</span></li>
          </ul>
        </div>
        <p className="lp-preview-why">Needs you because it costs $85, above the $50 limit.</p>
        <div className="lp-preview-actions" aria-hidden="true">
          <span className="lp-fake primary">Approve plan</span>
          <span className="lp-fake">Compare 4 sources</span>
        </div>
      </div>
      <figcaption>The first stall on the demo day, as the service manager sees it.</figcaption>
    </figure>
  )
}

/** The front page: what StallBreaker is, who it is for, how it works and how to try it (spec 115). */
export function Landing() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <a href="/" className="lp-logo"><Logo /> StallBreaker</a>
          <nav className="lp-links" aria-label="Sections">
            <a href="#how">How it works</a>
            <a href="#who">Who it is for</a>
            <a href="#why">Why it is different</a>
          </nav>
          <div className="lp-nav-actions">
            <ThemeToggle />
            <a className="lp-btn primary small" href="/demo">Open the demo</a>
          </div>
        </div>
      </header>

      <main>
        <section className="lp-hero">
          <div className="lp-wrap">
            <p className="lp-eyebrow">For dealership service departments</p>
            <h1>When a part goes missing, <span className="lp-grad">re-plan the day in seconds</span></h1>
            <p className="lp-lead">
              StallBreaker is a re-planning agent for car service shops. When a repair stops because a part is missing or late,
              it finds every place the part can come from, re-plans bays and technicians around it, and puts one plan in front
              of the service manager to approve.
            </p>
            <div className="lp-cta">
              <a className="lp-btn primary" href="/demo">Open the live demo <span aria-hidden="true">→</span></a>
              <a className="lp-btn secondary" href="#how">See how it works</a>
            </div>
            <p className="lp-hint">No sign-up. A simulated dealership day with 40 repair orders, 10 technicians and 10 bays.</p>
            <Preview />
          </div>
        </section>

        <section className="lp-section alt" aria-labelledby="problem-title">
          <div className="lp-wrap">
            <p className="lp-eyebrow">The problem</p>
            <h2 id="problem-title">The car is on the lift. The part is not on the shelf.</h2>
            <p className="lp-sub">A technician opens a job and finds a part missing or wrong. Three things go wrong at once.</p>
            <div className="lp-grid-3">
              <article className="lp-card"><h3>The bay is stuck</h3><p>A half-dismantled car cannot leave its lift, so the bay is lost until the part arrives.</p></article>
              <article className="lp-card"><h3>The afternoon starts to slip</h3><p>Technicians and bays are shared. One stalled job pushes others past the time their customers were promised.</p></article>
              <article className="lp-card"><h3>The fix is a round of phone calls</h3><p>Someone rings the other stores and the vendor and takes the first yes, without seeing what that choice does to the rest of the day.</p></article>
            </div>
          </div>
        </section>

        <section className="lp-section" id="how" aria-labelledby="how-title">
          <div className="lp-wrap">
            <p className="lp-eyebrow">How it works</p>
            <h2 id="how-title">From a technician’s note to an approved plan</h2>
            <ol className="lp-steps">
              {STEPS.map((s, i) => (
                <li key={s.title} className="lp-card">
                  <span className="lp-step-no" aria-hidden="true">{i + 1}</span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                  <p className="lp-example">{s.example}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="lp-section alt" id="who" aria-labelledby="who-title">
          <div className="lp-wrap">
            <p className="lp-eyebrow">Who it is for</p>
            <h2 id="who-title">Three people, one decision</h2>
            <div className="lp-grid-3">
              {ROLES.map((r) => (
                <article key={r.who} className="lp-card lp-role">
                  <span className="lp-role-icon"><Icon d={r.icon} /></span>
                  <h3>{r.who}</h3>
                  <p className="lp-role-verb">{r.verb}</p>
                  <p>{r.text}</p>
                </article>
              ))}
            </div>
            <p className="lp-note">In this prototype all three work from one screen.</p>
          </div>
        </section>

        <section className="lp-section" id="why" aria-labelledby="why-title">
          <div className="lp-wrap">
            <p className="lp-eyebrow">Why it is different</p>
            <h2 id="why-title">Answers you can check, not guesses</h2>
            <div className="lp-grid-2">
              {WHY.map((w) => (
                <article key={w.title} className="lp-why"><h3>{w.title}</h3><p>{w.text}</p></article>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section alt" aria-labelledby="numbers-title">
          <div className="lp-wrap">
            <p className="lp-eyebrow">On the demo day</p>
            <h2 id="numbers-title" className="visually-hidden">The demo day in numbers</h2>
            <ul className="lp-numbers">
              {NUMBERS.map((n) => <li key={n.value}><strong className="lp-grad">{n.value}</strong><span>{n.label}</span></li>)}
            </ul>
            <p className="lp-note">From the simulated demo day at 10:30. The shop data is simulated; part demand history is real.</p>
          </div>
        </section>

        <section className="lp-section" id="try" aria-labelledby="try-title">
          <div className="lp-wrap lp-try">
            <div>
              <p className="lp-eyebrow">Try it</p>
              <h2 id="try-title">See it work in two minutes</h2>
            </div>
            <ol className="lp-try-steps">
              <li>Open the demo. It is 10:30 at Main Street, a simulated dealership.</li>
              <li>RO-1013’s water pump gasket kit is out of stock and the car is due on the lift. Press <strong>See the options</strong> in the parts check.</li>
              <li>Compare the sources, preview the plan on the board, and approve it. Then try the note box: “1013 no gasket kit” works too.</li>
            </ol>
            <a className="lp-btn primary" href="/demo">Open the live demo <span aria-hidden="true">→</span></a>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <a href="/" className="lp-logo"><Logo /> StallBreaker</a>
          <p>Built for Tekion’s Tek Qubit 2026. All shop data is simulated; part demand history is real (Monash car parts dataset). Not connected to any dealer system.</p>
          <a href="https://github.com/danikadelacroix/stallbreaker">Source and specs on GitHub</a>
        </div>
      </footer>
    </div>
  )
}
