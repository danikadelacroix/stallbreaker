import { useEffect, useState } from 'react'
import type { IntakeInfo, NoteReading } from './types'
import { clock, getIntakeInfo, readNote } from './api'
import { useDictation } from './useDictation'

interface Props {
  busy: boolean
  /** The reading was confirmed: open the stall for this job and part. */
  onMissing: (roId: string, partId: string) => void
  /** The reading was confirmed: a part on its way will arrive at a new time. */
  onLate: (roId: string, partId: string, arrives: number) => void
  /** The reading was confirmed: the source said yes, or the part is here. */
  onAnswer: (roId: string, partId: string, answer: 'confirmed' | 'received') => void
  /** The reading was confirmed: the source cannot supply the part. */
  onCannotSupply: (roId: string, partId: string) => void
  /** The question above the box, and its example. Each role asks in its own words. */
  label?: string; placeholder?: string
  /** The readings this role acts on. Any other reading is shown with `notYours` instead of a yes button. */
  accept?: NoteReading['kind'][]; notYours?: string
  /** This role's wording for the yes button, by kind of reading. */
  yes?: Partial<Record<NoteReading['kind'], string>>
  /** Set when nothing can be reported right now, with the reason. */
  paused?: string | null
}

const YES: Record<NoteReading['kind'], string> = {
  missing_part: 'Yes, show the options', late_part: 'Yes, check the plan', confirmed: 'Yes, record it',
  received: 'Yes, record it', cannot_supply: 'Yes, see other sources', unclear: '',
}

/** One line on what the note was understood to say. */
function understood(r: NoteReading): string {
  const part = r.part_name!, from = r.source_name
  switch (r.kind) {
    case 'late_part': return `${part}${from ? ` from ${from}` : ''} will now arrive at ${clock(r.arrives_min!)}`
    case 'confirmed': return `${from} confirmed the ${part.toLowerCase()}`
    case 'received': return `The ${part.toLowerCase()} from ${from} is here`
    case 'cannot_supply': return `${from} cannot supply the ${part.toLowerCase()}`
    default: return `${part} is missing or wrong`
  }
}

/** A technician's note goes in, a reading comes out, and a person confirms it before anything else happens. */
const MicIcon = () => (
  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
  </svg>
)

export function IntakePanel({ busy, onMissing, onLate, onAnswer, onCannotSupply, label, placeholder, accept, notYours, yes, paused }: Props) {
  const [text, setText] = useState('')
  const [reading, setReading] = useState<NoteReading | null>(null)
  const [info, setInfo] = useState<IntakeInfo | null>(null)
  const [working, setWorking] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    getIntakeInfo().then((i) => { if (alive) setInfo(i) }).catch(() => { /* the box still works without the score line */ })
    return () => { alive = false }
  }, [])

  const read = () => {
    setWorking(true); setProblem(null); setReading(null)
    readNote(text.trim())
      .then(setReading)
      .catch((e: unknown) => setProblem(e instanceof Error ? e.message : 'Could not read the note'))
      .finally(() => setWorking(false))
  }
  const clear = () => { setReading(null); setText('') }
  const mic = useDictation((heard) => { setText(heard.slice(0, 600)); setReading(null) })
  const mine = !reading || reading.kind === 'unclear' || !accept || accept.includes(reading.kind)
  const outside = info?.eval?.[info.reader]?.outside

  return (
    <section className="intake" aria-label="Read a note">
      <div className="intake-in">
        <label htmlFor="note">{label ?? 'What did the technician or the source say?'}</label>
        <textarea id="note" rows={2} maxLength={600} value={text} disabled={busy || working}
          placeholder={mic.listening ? 'Listening…' : placeholder ?? 'For example: 1013 wp off, gskt kit in bin is for the 2.0 not 2.5t'}
          onChange={(e) => { setText(e.target.value); setReading(null) }} />
        <div className="intake-foot">
          <p className="muted small">
            {info?.sends_notes_out
              ? `Read by ${info.reader.replace('model: ', '')}. The note is sent to that provider; phone numbers, emails and VINs are removed first.`
              : 'Read by rules on this machine. Nothing is sent anywhere.'}
            {outside && ` On ${outside.of} test notes written by someone else, this reader got ${outside.right} right.`}
          </p>
          <div className="intake-buttons">
            {mic.supported && (
              <button type="button" className={`ghost mic ${mic.listening ? 'on' : ''}`} aria-pressed={mic.listening} disabled={busy || working} onClick={mic.toggle}>
                <MicIcon /> {mic.listening ? 'Stop' : 'Speak'}
              </button>
            )}
            <button type="button" className="primary" disabled={busy || working || text.trim().length === 0} onClick={read}>
              {working ? 'Reading…' : 'Read the note'}
            </button>
          </div>
        </div>
      </div>
      {mic.supported && <p className="muted small mic-note">{mic.problem ?? 'Speak uses this browser’s own speech service to turn your words into text. You still confirm what was understood.'}</p>}
      {problem && <p className="error" role="alert">{problem}</p>}
      {reading && (
        <div className={`reading ${reading.kind === 'unclear' ? 'unclear' : ''}`} role="status">
          {reading.kind === 'unclear' ? (
            <>
              <p className="eyebrow alert">Could not read this note</p>
              <p>{reading.why_unclear}</p>
              <p className="muted small">Nothing was opened. Pick the job on the board, or add the repair order number and try again.</p>
            </>
          ) : (
            <>
              <p className="eyebrow">Is this right?</p>
              <p className="understood">
                <strong>{reading.ro_id}</strong> · {reading.description} · {reading.vehicle}<br />
                <strong>{understood(reading)}</strong>
              </p>
              <p className="muted small">From the words “{reading.quote}”. Read by {reading.read_by.replace('model: ', '')}.</p>
              {!mine && <p className="fallback">{notYours}</p>}
              {mine && paused && <p className="fallback">{paused}</p>}
              <div className="actions">
                <button type="button" className="ghost" disabled={busy} onClick={() => setReading(null)}>{mine ? 'No, that is wrong' : 'Close'}</button>
                {mine && !paused && <button type="button" className="primary" disabled={busy} onClick={() => {
                  const ro = reading.ro_id!, part = reading.part_id!
                  if (reading.kind === 'late_part') onLate(ro, part, reading.arrives_min!)
                  else if (reading.kind === 'confirmed' || reading.kind === 'received') onAnswer(ro, part, reading.kind)
                  else if (reading.kind === 'cannot_supply') onCannotSupply(ro, part)
                  else onMissing(ro, part)
                  clear()
                }}>{yes?.[reading.kind] ?? YES[reading.kind]}</button>}
              </div>
            </>
          )}
          {reading.fell_back_because && (
            <p className="fallback small">The model was not used: {reading.fell_back_because}. Plain rules read this note instead.</p>
          )}
        </div>
      )}
    </section>
  )
}
