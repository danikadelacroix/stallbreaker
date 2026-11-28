import { useEffect, useState } from 'react'
import './roles.css'
import type { Day, Order, PartNeed, Proposal } from '../types'
import { answerRequest, clock, getDay, getProposal, reportStall } from '../api'
import { IntakePanel } from '../IntakePanel'
import { StartHere } from '../StartHere'
import { usePoll } from '../usePoll'
import { RoleBar } from './RoleBar'

const message = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong')
const STATUS: Record<Order['status'], string> = { done: 'Done', in_progress: 'In progress', scheduled: 'Up next', waiting_for_part: 'Waiting for a part', unplanned: 'Not planned' }
const ME = 'sb-technician'

/** Where one part stands, in a technician's words. No sources compared, no costs (spec 116 rule 5). */
function partLine(p: PartNeed, waiting: boolean): { text: string; tone: 'ok' | 'warn' | 'plain' } {
  if (waiting) return { text: 'Reported missing. The service manager is deciding.', tone: 'warn' }
  if (p.request?.state === 'received') return { text: `Here, from ${p.request.source_name}`, tone: 'ok' }
  if (p.request) return { text: `Arriving ${clock(p.request.arrives_min)} from ${p.request.source_name}`, tone: 'warn' }
  if (p.shortfall) return { text: 'Not on the shelf', tone: 'warn' }
  return { text: 'On the shelf', tone: 'plain' }
}

/** The technician's day: their own jobs, and a way to say what is missing (spec 116 rules 4 to 8). */
export function TechnicianView() {
  const [day, setDay] = useState<Day | null>(null)
  const [pending, setPending] = useState<Proposal | null>(null)
  const [me, setMe] = useState(() => { try { return localStorage.getItem(ME) ?? 'Pooja' } catch { return 'Pooja' } })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = async () => {
    const d = await getDay()
    setDay(d)
    setPending(d.open_proposal_id ? await getProposal(d.open_proposal_id) : null)
  }
  useEffect(() => { load().catch((e) => setError(message(e))) }, [])
  usePoll(() => { if (!busy) return load().catch(() => { /* the next round will try again */ }) })

  const run = async (work: () => Promise<void>) => {
    setBusy(true)
    try { await work(); setError(null) } catch (e) { setError(message(e)) } finally { setBusy(false) }
  }

  if (error && !day) return <main className="center"><p className="error" role="alert">Could not reach the StallBreaker API. ({error})</p></main>
  if (!day) return <main className="center"><p>Loading the day…</p></main>

  const paused = pending ? `The service manager is still deciding ${pending.ro_id}. You can report the next one after that.` : null
  const report = (roId: string, partId: string) => run(async () => {
    const p = await reportStall(roId, partId)
    setPending(p); setDay(await getDay())
    setNotice(`Sent to the service manager: ${p.part_name} for ${roId}. You will see the new time here once a plan is approved.`)
  })
  const here = (roId: string, partId: string) => run(async () => {
    setDay(await answerRequest(roId, partId, 'received'))
    setNotice(`Recorded: the part for ${roId} is here.`)
  })
  const pick = (name: string) => { setMe(name); try { localStorage.setItem(ME, name) } catch { /* this visit only */ } }

  const mine = day.orders.filter((o) => o.technician === me).sort((a, b) => (a.start_min ?? 0) - (b.start_min ?? 0))
  const open = mine.filter((o) => o.status !== 'done')
  const done = mine.filter((o) => o.status === 'done')

  return (
    <>
      <RoleBar role="technician" store={day.store.name}><span className="role-clock">{clock(day.now_min)}</span></RoleBar>
      <main className="role-main narrow">
        {error && <p className="error" role="alert">{error}</p>}
        {notice && <p className="notice" role="status">{notice}</p>}
        <StartHere id="sb-guide-technician">
          <p>You are a technician at Main Street and it is {clock(day.now_min)}. Below are your jobs for today.</p>
          <ol>
            <li>As Pooja, your next job is RO-1013 and its gasket kit is not on the shelf. Say or type it: “1013 no gasket kit”.</li>
            <li>Confirm what was understood. It goes to the service manager, who picks the plan.</li>
            <li>Come back here to see your new time and bay.</li>
          </ol>
        </StartHere>

        <div className="who">
          <label htmlFor="who">I am</label>
          <select id="who" value={me} onChange={(e) => pick(e.target.value)}>
            {day.technicians.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <span className="muted small">{open.length} {open.length === 1 ? 'job' : 'jobs'} left today</span>
        </div>

        <IntakePanel busy={busy} label="What is wrong? Say it or type it." placeholder="For example: 1013 no gasket kit in the bin"
          accept={['missing_part', 'received']} notYours="That sounds like news from a source. Pass it to the parts counter."
          yes={{ missing_part: 'Yes, send to the service manager', received: 'Yes, it is here' }} paused={paused}
          onMissing={(ro, part) => void report(ro, part)} onAnswer={(ro, part) => void here(ro, part)}
          onLate={() => undefined} onCannotSupply={() => undefined} />

        <h2 className="role-h">My jobs</h2>
        {open.length === 0 && <p className="muted">No open jobs for {me} today.</p>}
        <ul className="jobs">
          {open.map((o) => {
            const waiting = pending?.ro_id === o.id
            return (
              <li key={o.id} className={`job ${o.status}`}>
                <div className="job-head">
                  <div>
                    <p className="job-id">{o.id} · {o.bay} · {o.start_min !== null ? `${clock(o.start_min)} to ${clock(o.end_min!)}` : 'not planned'}</p>
                    <h3>{o.description}</h3>
                    <p className="muted">{o.vehicle} · promised {clock(o.promise_min)}</p>
                  </div>
                  <span className={`badge ${waiting || o.status === 'waiting_for_part' ? 'warn' : 'ok'}`}>{waiting ? 'Waiting for a decision' : STATUS[o.status]}</span>
                </div>
                {o.late && <p className="job-late">This job will finish after its promise time.</p>}
                {o.parts.length > 0 && (
                  <ul className="job-parts">
                    {o.parts.map((p) => {
                      const line = partLine(p, waiting && pending?.part_id === p.part_id)
                      return (
                        <li key={p.part_id}>
                          <div><span>{p.name}</span><span className={`part-state ${line.tone}`}>{line.text}</span></div>
                          {!p.request && !waiting && <button type="button" className="link" disabled={busy || !!pending} onClick={() => void report(o.id, p.part_id)}>Report missing</button>}
                          {p.request && p.request.state !== 'received' && <button type="button" className="link" disabled={busy} onClick={() => void here(o.id, p.part_id)}>It is here</button>}
                        </li>
                      )
                    })}
                  </ul>
                )}
              </li>
            )
          })}
        </ul>
        {paused && <p className="muted small">{paused}</p>}
        {done.length > 0 && <p className="muted done-line">Done today: {done.map((o) => `${o.id} ${o.description}`).join(' · ')}</p>}
      </main>
    </>
  )
}
