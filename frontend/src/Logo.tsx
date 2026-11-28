// The StallBreaker mark: a 12-hour dial with one hour lifted out and moved. The day, with one job re-planned.
// The ring is 12 dashes on a circle of radius 14 (circumference 87.96): 11 dashes drawn, the 12th left as a gap,
// and that 12th segment drawn again in orange, pushed outward.
const RING = '5.6 1.73 '.repeat(10) + '5.6 9.06'
const ORANGE = '#FF5A1F'

/** The dial mark. `tile` draws it on its warm-black square; without it the ring takes the text colour. */
export function Logo({ size = 28, tile = true }: { size?: number; tile?: boolean }) {
  const ring = tile ? '#F3F0E8' : 'currentColor'
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" className="logo-mark">
      {tile && <rect width="48" height="48" rx="10" fill="#15130F" />}
      <circle cx="24" cy="24" r="14" fill="none" stroke={ring} strokeWidth="5.5" strokeDasharray={RING} />
      <path d="M36.12 17A14 14 0 0 1 37.89 22.27" fill="none" stroke={ORANGE} strokeWidth="5.5" transform="translate(4.3 -1.2)" />
      <circle cx="24" cy="24" r="2.4" fill={ORANGE} />
    </svg>
  )
}

/** The mark and the name together. */
export function Wordmark({ size = 28 }: { size?: number }) {
  return <span className="wordmark"><Logo size={size} /><span>StallBreaker</span></span>
}
