import { createContext, useContext } from 'react'
import type { PrintRequest } from './registry'

export type PrintContextValue = { openPrintView: (request: PrintRequest) => void }
export const PrintContext = createContext<PrintContextValue | null>(null)

export function usePrintView() {
  const value = useContext(PrintContext)
  return (request: PrintRequest) => {
    if (!value) throw new Error('PrintProvider is missing')
    value.openPrintView(request)
  }
}
