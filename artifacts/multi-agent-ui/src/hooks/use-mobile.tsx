// Custom hook: returns true when the viewport width is below the mobile breakpoint.
// Subscribes to the matchMedia change event so it re-renders on resize.

import * as React from "react"

const MOBILE_BREAKPOINT = 768  // pixels — matches Tailwind's 'md' breakpoint

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    // Create a media query that fires whenever the viewport crosses the breakpoint
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)  // update state on every resize
    }
    mql.addEventListener("change", onChange)
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)    // set initial value immediately
    return () => mql.removeEventListener("change", onChange)  // clean up listener on unmount
  }, [])

  return !!isMobile  // coerce undefined → false on first render
}
