import { useEffect, useState } from 'react'
import type { IntakeInfo, NoteReading } from './types'
import { clock, getIntakeInfo, readNote } from './api'

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
export function IntakePanel({ busy, onMissing, onLate, onAnswer, onCannotSupply }: Props) {
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
  const outside = info?.eval?.[info.reader]?.outside

  return (
    <section className="intake" aria-label="Read a note">
      <div className="intake-in">
        <label htmlFor="note">What did the technician or the source say?</label>
        <textarea id="note" rows={2} maxLength={600} value={text} disabled={busy || working}
          placeholder="For example: 1013 wp off, gskt kit in bin is for the 2.0 not 2.5t"
          onChange={(e) => { setText(e.target.value); setReading(null) }} />
        <div className="intake-foot">
          <p className="muted small">
            {info?.sends_notes_out
              ? `Read by ${info.reader.replace('model: ', '')}. The note is sent to that provider; phone numbers, emails and VINs are removed first.`
              : 'Read by rules on this machine. Nothing is sent anywhere.'}
            {outside && ` On ${outside.of} test notes written by someone else, this reader got ${outside.right} right.`}
          </p>
          <button type="button" className="primary" disabled={busy || working || text.trim().length === 0} onClick={read}>
            {working ? 'Reading…' : 'Read the note'}
          </button>
        </div>
      </div>
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
              <div className="actions">
                <button type="button" className="ghost" disabled={busy} onClick={() => setReading(null)}>No, that is wrong</button>
                <button type="button" className="primary" disabled={busy} onClick={() => {
                  const ro = reading.ro_id!, part = reading.part_id!
                  if (reading.kind === 'late_part') onLate(ro, part, reading.arrives_min!)
                  else if (reading.kind === 'confirmed' || reading.kind === 'received') onAnswer(ro, part, reading.kind)
                  else if (reading.kind === 'cannot_supply') onCannotSupply(ro, part)
                  else onMissing(ro, part)
                  clear()
                }}>{YES[reading.kind]}</button>
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
