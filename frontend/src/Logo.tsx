/** The StallBreaker mark: a broken bar, bridged. */
export function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true" className="logo-mark">
      <defs>
        <linearGradient id="sb-logo" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#14a394" />
          <stop offset="1" stopColor="#3b63c4" />
        </linearGradient>
      </defs>
      <rect width="28" height="28" rx="8" fill="url(#sb-logo)" />
      <rect x="6" y="8.5" width="9" height="3.5" rx="1.75" fill="#fff" />
      <rect x="13" y="16" width="9" height="3.5" rx="1.75" fill="#fff" />
      <path d="M14.5 12 L13.5 16" stroke="#fff" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}
