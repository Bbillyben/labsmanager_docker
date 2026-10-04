import { lazy, Suspense, useCallback, useRef, useState, type ReactNode } from 'react'
import type { PrintRequest } from './registry'
import { PrintContext } from './printContext'
import styles from './print.module.css'

const PrintShell = lazy(() => import('./PrintShell').then((module) => ({ default: module.PrintShell })))

export function PrintProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<PrintRequest | null>(null)
  const trigger = useRef<HTMLElement | null>(null)
  const openPrintView = useCallback((next: PrintRequest) => {
    trigger.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setRequest(next)
  }, [])
  const closePrintView = () => {
    setRequest(null)
    requestAnimationFrame(() => trigger.current?.focus())
  }
  return <PrintContext.Provider value={{ openPrintView }}>
    <div aria-hidden={request ? true : undefined} className={request ? styles.backgroundHidden : undefined} inert={request ? true : undefined}>{children}</div>
    {request && <Suspense fallback={null}><PrintShell request={request} onClose={closePrintView} /></Suspense>}
  </PrintContext.Provider>
}
