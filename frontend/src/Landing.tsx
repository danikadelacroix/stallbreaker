import './landing.css'
import { Wordmark } from './Logo'
import { ThemeToggle } from './theme'

const STEPS = [
  { title: 'Report it', text: 'The technician says what is wrong in their own words. StallBreaker reads it into a job and a part, quotes the words it relied on, and opens nothing until someone confirms.',
    example: '“1013 wp off, gskt kit in bin is for the 2.0 not 2.5t”' },
  { title: 'Find every source', text: 'Sister stores, the local vendor and the OEM depot, each with arrival time and cost. A sister store is marked unsafe to borrow from when lending would likely leave it short, judged from 51 months of real part demand.',
    example: '4 sources · 1 unsafe to lend' },
  { title: 'Re-plan the day', text: 'One optimisation chooses the source and moves the other jobs at the same time, so the fewest customer promises are missed. Every plan is checked against the shop’s rules and proven best, usually in under a second.',
    example: 'Proven best in 0.08 s' },
  { title: 'Approve and follow up', text: 'The service manager approves one plan. The parts counter tracks the order from requested to confirmed to received, and sees the last moment to switch to a backup source.',
    example: 'Switch to the vendor by 11:15 if North goes quiet' },
]

const ROLES = [
  { view: 'manager', who: 'Service manager', verb: 'Decides', text: 'Sees the recommended plan, what it trades off, and what waiting would cost. Nothing is ordered or moved without their approval.' },
  { view: 'technician', who: 'Technician', verb: 'Reports', text: 'Types or dictates what is missing, the way they would tell a colleague, and gets back to the next job.' },
  { view: 'parts', who: 'Parts counter', verb: 'Follows up', text: 'Sees every ordered part as requested, confirmed or received, records what the source said, and knows when to chase.' },
]

const WHY = [
  { title: 'Proven best, not a rule of thumb', text: 'A constraint solver plans the part source and the schedule together. Every plan says whether it is proven best and how long that took.' },
  { title: 'Shows its working', text: 'For every source it did not pick, you see what the day would look like with it and the one reason it lost.' },
  { title: 'Knows how much room there is', text: 'Each plan says how late the part can be before another promise is lost, and when to switch if the source goes quiet.' },
  { title: 'A person stays in charge', text: 'Reading a note saves nothing, every plan waits for approval, and the app never contacts a supplier on its own.' },
]

/** Minutes after 08:00 as a share of the 08:00 to 16:00 strip. */
const at = (min: number) => `${(min / 480) * 100}%`
const span = (from: number, to: number) => ({ left: at(from), width: at(to - from) })

/** The first stall of the demo day, as it looks after the plan: RO-1013 moved to Bay 4, RO-1024 into Bay 7. */
function BoardStill() {
  return (
    <figure className="lp-still">
      <div className="lp-board" aria-hidden="true">
        <div className="lp-board-head"><span>Bay board · Main Street</span><span>Plan preview · 10:30</span></div>
        <div className="lp-board-grid">
          <div className="lp-axis">{[8, 12, 16].map((h) => <span key={h} style={{ left: at((h - 8) * 60) }}>{String(h).padStart(2, '0')}:00</span>)}</div>
          <div className="lp-row"><span className="lp-row-label">Bay 6</span><div className="lp-track">
            <span className="lp-bar done" style={span(0, 45)}><b>1010</b></span>
            <span className="lp-bar busy" style={span(60, 170)}><b>1029</b><span className="lp-bar-text">Control arm</span></span>
            <span className="lp-bar sched" style={span(170, 250)}><b>1036</b><span className="lp-bar-text">AC</span></span>
            <span className="lp-bar sched" style={span(255, 405)}><b>1017</b><span className="lp-bar-text">Timing belt</span></span>
          </div></div>
          <div className="lp-row"><span className="lp-row-label">Bay 7</span><div className="lp-track">
            <span className="lp-bar done" style={span(0, 120)}><b>1002</b></span>
            <span className="lp-bar moved" style={span(200, 310)}><b>1024</b><span className="lp-bar-text">Control arm</span></span>
            <span className="lp-bar sched" style={span(330, 420)}><b>1040</b><span className="lp-bar-text">Pads</span></span>
          </div></div>
          <div className="lp-row"><span className="lp-row-label">Bay 4</span><div className="lp-track">
            <span className="lp-bar done" style={span(0, 120)}><b>1008</b></span>
            <span className="lp-bar sched" style={span(150, 200)}><b>1039</b></span>
            <span className="lp-bar moved" style={span(210, 390)}><b>1013</b><span className="lp-bar-text">Water pump</span></span>
          </div></div>
          <span className="lp-now" style={{ left: `calc(var(--lbl) + (100% - var(--lbl)) * ${150 / 480})` }}><i>10:30</i></span>
        </div>
      </div>
      <div className="lp-ticket">
        <p className="lp-ticket-head"><span>Part missing · 10:30</span><span>RO-1013</span></p>
        <p className="lp-ticket-title">Water pump gasket kit</p>
        <p className="lp-ticket-sub">2020 Ford Explorer · was due in Bay 7 at 10:30</p>
        <dl>
          <div><dt>Source</dt><dd>Local vendor · 11:30 · $85</dd></div>
          <div><dt>Promises missed</dt><dd>1 <s>2</s></dd></div>
          <div><dt>Late minutes</dt><dd>30 <s>375</s></dd></div>
          <div><dt>Proven best in</dt><dd>0.08 s</dd></div>
        </dl>
        <span className="lp-ticket-btn" aria-hidden="true">Approve plan</span>
      </div>
      <figcaption>The first stall of the demo day. RO-1013 moves to Bay 4 at 11:30 and RO-1024 takes Bay 7: one promise is missed instead of two.</figcaption>
    </figure>
  )
}

const Label = ({ n, children }: { n: string; children: string }) => <p className="lp-label"><span>{n}</span>{children}</p>

/** The front page: what StallBreaker is, who it is for, how it works and how to try it (spec 115). */
export function Landing() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <a href="/" className="lp-home" aria-label="StallBreaker home"><Wordmark /></a>
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
          <div className="lp-wrap lp-hero-grid">
            <div className="lp-hero-copy">
              <p className="lp-kicker"><span className="lp-dot" aria-hidden="true" />Re-planning agent for dealership service departments</p>
              <h1>When a part goes missing, re-plan the day <u>in seconds</u>.</h1>
              <p className="lp-lead">
                When a repair stops because a part is missing or late, StallBreaker finds every place the part can come from,
                re-plans bays and technicians around it, and puts one plan in front of the service manager to approve.
              </p>
              <div className="lp-cta">
                <a className="lp-btn primary" href="/demo">Open the live demo <span aria-hidden="true">→</span></a>
                <a className="lp-textlink" href="#how">How it works <span aria-hidden="true">↓</span></a>
              </div>
              <p className="lp-hint">No sign-up · simulated dealership · 40 repair orders · 10 technicians · 10 bays</p>
            </div>
            <BoardStill />
          </div>
        </section>

        <section className="lp-section" aria-labelledby="problem-title">
          <div className="lp-wrap lp-split">
            <div>
              <Label n="01">The problem</Label>
              <h2 id="problem-title">The car is on the lift. The part is not on the shelf.</h2>
            </div>
            <ol className="lp-problems">
              <li><h3>The bay is stuck</h3><p>A half-dismantled car cannot leave its lift, so the bay is lost until the part arrives.</p></li>
              <li><h3>The afternoon starts to slip</h3><p>Technicians and bays are shared. One stalled job pushes others past the time their customers were promised.</p></li>
              <li><h3>The fix is a round of phone calls</h3><p>Someone rings the other stores and the vendor and takes the first yes, without seeing what that choice does to the rest of the day.</p></li>
            </ol>
          </div>
        </section>

        <section className="lp-section lp-alt" id="how" aria-labelledby="how-title">
          <div className="lp-wrap">
            <Label n="02">How it works</Label>
            <h2 id="how-title">From a technician’s note to an approved plan</h2>
            <ol className="lp-steps">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <span className="lp-step-no">{String(i + 1).padStart(2, '0')}</span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                  <p className="lp-example">{s.example}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="lp-section" id="who" aria-labelledby="who-title">
          <div className="lp-wrap">
            <Label n="03">Who it is for</Label>
            <h2 id="who-title">Three people, one decision</h2>
            <div className="lp-roles">
              {ROLES.map((r) => (
                <article key={r.who}>
                  <p className="lp-role-verb">{r.verb}</p>
                  <h3>{r.who}</h3>
                  <p>{r.text}</p>
                  <p className="lp-role-link"><a href={`/demo/${r.view}`}>Open the {r.who.toLowerCase()}’s view <span aria-hidden="true">→</span></a></p>
                </article>
              ))}
            </div>
            <p className="lp-note">Each has their own view in the demo, and all three share the same day.</p>
          </div>
        </section>

        <section className="lp-section lp-alt" id="why" aria-labelledby="why-title">
          <div className="lp-wrap">
            <Label n="04">Why it is different</Label>
            <h2 id="why-title">Answers you can check, not guesses</h2>
            <div className="lp-why">
              {WHY.map((w) => <article key={w.title}><h3>{w.title}</h3><p>{w.text}</p></article>)}
            </div>
          </div>
        </section>

        <section className="lp-band" aria-labelledby="numbers-title">
          <div className="lp-wrap">
            <p className="lp-label"><span>05</span>On the demo day</p>
            <h2 id="numbers-title" className="visually-hidden">The demo day in numbers</h2>
            <ul className="lp-numbers">
              <li><strong>2<em>→</em>1</strong><span>promises missed on the first stall, without and with a re-plan</span></li>
              <li><strong>375<em>→</em>30</strong><span>late minutes on the same stall</span></li>
              <li><strong>&lt;1s</strong><span>to a plan that is proven best</span></li>
              <li><strong>77</strong><span>automated checks behind the rules</span></li>
            </ul>
            <p className="lp-band-note">From the simulated demo day at 10:30. The shop data is simulated; part demand history is real.</p>
          </div>
        </section>

        <section className="lp-section" id="try" aria-labelledby="try-title">
          <div className="lp-wrap lp-split">
            <div>
              <Label n="06">Try it</Label>
              <h2 id="try-title">See it work in two minutes</h2>
            </div>
            <div>
              <ol className="lp-try-steps">
                <li>Open the demo and continue as the service manager. It is 10:30 at Main Street, a simulated dealership.</li>
                <li>RO-1013’s water pump gasket kit is out of stock and the car is due on the lift. Press <strong>See the options</strong> in the parts check.</li>
                <li>Compare the sources, preview the plan on the board, and approve it. Then switch to the technician and say it instead: “1013 no gasket kit”.</li>
              </ol>
              <a className="lp-btn primary" href="/demo">Open the live demo <span aria-hidden="true">→</span></a>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap lp-footer-inner">
          <Wordmark size={24} />
          <p>Built for Tekion’s Tek Qubit 2026. All shop data is simulated; part demand history is real (Monash car parts dataset). Not connected to any dealer system.</p>
          <a href="https://github.com/danikadelacroix/stallbreaker">Source and specs on GitHub</a>
        </div>
      </footer>
    </div>
  )
}
