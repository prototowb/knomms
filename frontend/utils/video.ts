/** Timestamp deep links for video sources (docs/15, OQ-61). */

export function tsLocatorSeconds(locator: string): number | null {
  const m = /^ts:(\d{2}):(\d{2}):(\d{2})$/.exec(locator)
  if (!m) return null
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3])
}

/** `watch?v=…&t=Ns` link for a ts: locator on a video source, else null. */
export function videoDeepLink(url: string | null | undefined, locator: string): string | null {
  if (!url) return null
  const secs = tsLocatorSeconds(locator)
  if (secs === null) return null
  return `${url}${url.includes('?') ? '&' : '?'}t=${secs}s`
}
