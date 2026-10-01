import { Ellipsis, Pencil, Trash2 } from 'lucide-react'
import type { ComponentProps } from 'react'
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
  onTrigger?: (trigger: HTMLElement) => void
  finalFocus?: ComponentProps<typeof DropdownMenuContent>['finalFocus']
}

export function ItemActionMenu({ label, canChange, canDelete, adminUrl, onOpen, onEdit, onDelete, onTrigger, finalFocus }: Props) {
  const { t } = useTranslation()
  if (!canChange && !canDelete && !adminUrl) return null
  return <DropdownMenu onOpenChange={(open) => { if (open) onOpen() }}>
    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={label} onClick={(event) => onTrigger?.(event.currentTarget)}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
    <DropdownMenuContent align="end" finalFocus={finalFocus}>
      {canChange && <DropdownMenuItem onClick={onEdit}><Pencil aria-hidden="true" />{t('common.edit')}</DropdownMenuItem>}
      {canDelete && <DropdownMenuItem onClick={onDelete}><Trash2 aria-hidden="true" />{t('common.delete')}</DropdownMenuItem>}
      {adminUrl && <>{(canChange || canDelete) && <DropdownMenuSeparator />}<AdminObjectAction adminUrl={adminUrl} /></>}
    </DropdownMenuContent>
  </DropdownMenu>
}
