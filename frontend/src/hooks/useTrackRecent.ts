import { useEffect, useRef } from 'react'
import { trackRecentItem, type RecentUrlId } from '../api/recentItems'

/** Call only from a page whose destination has actually loaded or been selected. */
export function useTrackRecent(urlId: RecentUrlId, objId?: number, ready = true) {
  const last = useRef<string | null>(null)
  useEffect(() => {
    if (!ready) {
      if (objId === undefined) last.current = null
      return
    }
    const key = `${urlId}:${objId ?? ''}`
    if (last.current === key) return
    last.current = key
    void trackRecentItem(urlId, objId).catch(() => { /* Recent history must never block the destination. */ })
  }, [urlId, objId, ready])
}
