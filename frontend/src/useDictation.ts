import { useRef, useState } from 'react'

// The browser's own speech recognition (Chrome, Edge, Safari). It is not in TypeScript's DOM types.
interface Recognition {
  lang: string; interimResults: boolean; continuous: boolean
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null
  onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null
  start(): void; stop(): void
}
type RecognitionClass = new () => Recognition
const Recognizer = (): RecognitionClass | undefined => {
  const w = window as unknown as { SpeechRecognition?: RecognitionClass; webkitSpeechRecognition?: RecognitionClass }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

/** Push to talk: the browser turns speech into text and hands it over as it goes (spec 116 rules 13, 14). */
export function useDictation(onText: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [problem, setProblem] = useState<string | null>(null)
  const active = useRef<Recognition | null>(null)
  const supported = typeof window !== 'undefined' && !!Recognizer()

  const stop = () => active.current?.stop()
  const start = () => {
    const Rec = Recognizer()
    if (!Rec) return
    const rec = new Rec()
    rec.lang = 'en-IN'; rec.interimResults = true; rec.continuous = false
    rec.onresult = (e) => onText(Array.from(e.results).map((r) => r[0].transcript).join(' ').trim())
    rec.onerror = (e) => setProblem(e.error === 'not-allowed' ? 'The microphone is blocked for this site. Allow it in the browser, or type instead.'
      : e.error === 'no-speech' ? 'Nothing was heard. Try again, or type instead.' : 'Could not listen. Type instead.')
    rec.onend = () => { setListening(false); active.current = null }
    active.current = rec; setProblem(null); setListening(true)
    try { rec.start() } catch { setListening(false); setProblem('Could not listen. Type instead.') }
  }
  return { supported, listening, problem, toggle: () => (listening ? stop() : start()) }
}
