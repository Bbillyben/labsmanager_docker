import { AlertDialog } from '@base-ui/react/alert-dialog'
import type { ReactNode, RefObject } from 'react'
import { useTranslation } from '../../i18n/i18n'
import { Button } from '../../ui/Button'

export function ConfirmDialog({ title, description, pending, error, onConfirm, onCancel, returnFocus }: {
  title: string; description: string; pending: boolean; error?: ReactNode
  onConfirm: () => void; onCancel: () => void; returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  return <AlertDialog.Root open onOpenChange={(open) => { if (!open && !pending) onCancel() }}>
    <AlertDialog.Portal>
      <AlertDialog.Backdrop className="fixed inset-0 z-50 bg-black/45" />
      <AlertDialog.Viewport className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <AlertDialog.Popup finalFocus={returnFocus} className="w-full max-w-md rounded-lg border border-border bg-background p-6 text-foreground shadow-xl">
          <AlertDialog.Title className="text-lg font-semibold">{title}</AlertDialog.Title>
          <AlertDialog.Description className="my-4 text-sm text-muted-foreground">{description}</AlertDialog.Description>
          {error}
          <div className="mt-4 flex justify-end gap-2">
            <Button autoFocus disabled={pending} onClick={onCancel}>{t('genericInfo.cancel')}</Button>
            <Button variant="destructive" disabled={pending} onClick={onConfirm}>{t(pending ? 'genericInfo.pending' : 'genericInfo.delete')}</Button>
          </div>
        </AlertDialog.Popup>
      </AlertDialog.Viewport>
    </AlertDialog.Portal>
  </AlertDialog.Root>
}
