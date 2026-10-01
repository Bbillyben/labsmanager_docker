import { Ellipsis } from 'lucide-react'
import type { ComponentProps, ReactNode } from 'react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu'
import { Button } from '../ui/Button'
import { AdminObjectAction } from './AdminObjectAction'

export type EntityAction = { id: string; label: string; icon?: ReactNode; disabled?: boolean; onSelect: () => void }
export type EntityActionGroup = EntityAction[]

export function EntityActionMenu({ label, groups, adminUrl, onTrigger, finalFocus }: {
  label: string
  groups: EntityActionGroup[]
  adminUrl?: string | null
  onTrigger?: (trigger: HTMLElement) => void
  finalFocus?: ComponentProps<typeof DropdownMenuContent>['finalFocus']
}) {
  const visible = groups.filter((group) => group.length > 0)
  if (!visible.length && !adminUrl) return null
  return <DropdownMenu>
    <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={label} onClick={(event) => onTrigger?.(event.currentTarget)}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
    <DropdownMenuContent align="end" finalFocus={finalFocus}>
      {visible.map((group, index) => <DropdownMenuGroup key={group.map((action) => action.id).join(':')}>
        {index > 0 && <DropdownMenuSeparator />}
        {group.map((action) => <DropdownMenuItem key={action.id} disabled={action.disabled} onClick={action.onSelect}>{action.icon}{action.label}</DropdownMenuItem>)}
      </DropdownMenuGroup>)}
      {adminUrl && <>{visible.length > 0 && <DropdownMenuSeparator />}<AdminObjectAction adminUrl={adminUrl} /></>}
    </DropdownMenuContent>
  </DropdownMenu>
}
