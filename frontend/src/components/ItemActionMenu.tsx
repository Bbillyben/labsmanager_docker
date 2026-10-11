import { Ellipsis, Pencil, Trash2 } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu'
import { AdminObjectAction } from './AdminObjectAction'
import { Button } from '../ui/Button'
import { useTranslation } from '../i18n/i18n'

type Props = {
  label: string
  canChange: boolean
  canDelete: boolean
  adminUrl?: string | null
  onOpen: () => void
  onEdit: () => void
  onDelete: () => void
  extraAction?: { label: string; icon: ReactNode; onSelect: () => void }
  onTrigger?: (trigger: HTMLElement) => void
  finalFocus?: ComponentProps<typeof DropdownMenuContent>['finalFocus']
}

export function ItemActionMenu({ label, canChange, canDelete, adminUrl, onOpen, onEdit, onDelete, extraAction, onTrigger, finalFocus }: Props) {
  const { t } = useTranslation()
  if (!canChange && !canDelete && !adminUrl && !extraAction) return null
  return <DropdownMenu onOpenChange={(open) => { if (open) onOpen() }}>
    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={label} onClick={(event) => onTrigger?.(event.currentTarget)}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
    <DropdownMenuContent align="end" finalFocus={finalFocus}>
      {canChange && <DropdownMenuItem onClick={onEdit}><Pencil aria-hidden="true" />{t('common.edit')}</DropdownMenuItem>}
      {canDelete && <DropdownMenuItem onClick={onDelete}><Trash2 aria-hidden="true" />{t('common.delete')}</DropdownMenuItem>}
      {extraAction && <DropdownMenuItem onClick={extraAction.onSelect}>{extraAction.icon}{extraAction.label}</DropdownMenuItem>}
      {adminUrl && <>{(canChange || canDelete || extraAction) && <DropdownMenuSeparator />}<AdminObjectAction adminUrl={adminUrl} /></>}
    </DropdownMenuContent>
  </DropdownMenu>
}
