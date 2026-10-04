import { Printer } from 'lucide-react'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { usePrintView } from './printContext'
import type { PrintRequest } from './registry'

export function PrintButton({ createRequest, disabled = false }: { createRequest: () => PrintRequest; disabled?: boolean }) {
  const { t } = useTranslation()
  const openPrintView = usePrintView()
  return <Button disabled={disabled} onClick={() => openPrintView(createRequest())} size="sm" variant="secondary"><Printer aria-hidden="true" />{t('print.action')}</Button>
}
