import { useEffect, useRef } from 'react'

/** Run `work` every few seconds while the tab is visible, so one role sees what another did (spec 116 rule 3). */
export function usePoll(work: () => void | Promise<void>, ms = 4000) {
  const latest = useRef(work)
  latest.current = work
  useEffect(() => {
    const id = window.setInterval(() => { if (document.visibilityState === 'visible') void latest.current() }, ms)
    return () => window.clearInterval(id)
  }, [ms])
}
