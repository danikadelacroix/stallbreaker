import '../landing.css'
import './roles.css'
import { Wordmark } from '../Logo'
import { ThemeToggle } from '../theme'
import { ROLES } from './RoleBar'

/** The first screen of the demo: who are you today? (spec 116 rules 1, 2) */
export function RolePicker() {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-wrap lp-nav-inner">
          <a href="/" className="lp-home" aria-label="StallBreaker home"><Wordmark /></a>
          <div className="lp-nav-actions"><ThemeToggle /></div>
        </div>
      </header>
      <main>
        <section className="lp-wrap picker">
          <p className="lp-kicker"><span className="lp-dot" aria-hidden="true" />Main Street · a simulated dealership · 10:30</p>
          <h1>Who are you today?</h1>
          <p className="lp-lead">Three people handle a stalled job. Pick one to see the day from where they stand. You can switch at any time, and all three share the same day.</p>
          <ol className="picker-roles">
            {ROLES.map((r, i) => (
              <li key={r.id}>
                <a href={`/demo/${r.id}`}>
                  <span className="lp-step-no">{String(i + 1).padStart(2, '0')} · {r.verb}</span>
                  <strong>{r.name}</strong>
                  <span className="picker-does">{r.does}</span>
                  <span className="picker-go">Continue as {r.name.toLowerCase()} <span aria-hidden="true">→</span></span>
                </a>
              </li>
            ))}
          </ol>
          <p className="lp-note">New here? Start as the service manager. These are demo roles: there is no sign-in, and nothing leaves this simulated shop.</p>
        </section>
      </main>
    </div>
  )
}
