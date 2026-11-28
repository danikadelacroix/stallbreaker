import type { ReactNode } from 'react'
import { Logo } from '../Logo'
import { ThemeToggle } from '../theme'

export type Role = 'manager' | 'technician' | 'parts'
export const ROLES: { id: Role; name: string; verb: string; does: string }[] = [
  { id: 'manager', name: 'Service manager', verb: 'Decides', does: 'See what needs a decision, compare the plans on the board, and approve one.' },
  { id: 'technician', name: 'Technician', verb: 'Reports', does: 'See your jobs for the day and report a missing part by voice or text.' },
  { id: 'parts', name: 'Parts counter', verb: 'Follows up', does: 'Track every ordered part, record what the source said, and order ahead.' },
]

/** Links to the three role views; the current one is marked (spec 116 rule 1). */
export function RoleNav({ role }: { role: Role }) {
  return (
    <nav className="role-nav" aria-label="Role">
      {ROLES.map((r) => <a key={r.id} href={`/demo/${r.id}`} aria-current={r.id === role ? 'page' : undefined}>{r.name}</a>)}
    </nav>
  )
}

/** The top bar of the technician and parts counter views. */
export function RoleBar({ role, store, children }: { role: Role; store: string; children?: ReactNode }) {
  return (
    <header className="top">
      <a href="/" className="brand brand-link" aria-label="StallBreaker home">
        <Logo size={32} />
        <div>
          <h1>StallBreaker</h1>
          <p>{store} · {ROLES.find((r) => r.id === role)!.name.toLowerCase()} · simulated data</p>
        </div>
      </a>
      <div className="top-actions">
        {children}
        <RoleNav role={role} />
        <ThemeToggle />
      </div>
    </header>
  )
}
