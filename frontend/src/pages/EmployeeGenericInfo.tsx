import { useRef, useState, type RefObject } from 'react'
import { Ellipsis, Pencil, Plus, Trash2 } from 'lucide-react'
import { deleteEmployeeGenericInfo, getEmployeeGenericInfo, type EmployeeGenericInfo as Info } from '../api/employees'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { CopyableValue } from '../components/common/CopyableValue'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../components/ui/dropdown-menu'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { GenericInfoFormSheet } from './GenericInfoFormSheet'
import { genericInfoIcon } from './genericInfoIcons'
import { useEmployeeResource } from './useEmployeeResource'
import styles from './EmployeeGenericInfo.module.css'

export function EmployeeGenericInfo({ employeeId }: { employeeId: string }) {
  const { t } = useTranslation()
  const resource = useEmployeeResource(employeeId, getEmployeeGenericInfo)
  const [selected, setSelected] = useState<number | null>(null)
  const [editing, setEditing] = useState<Info | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Info | null>(null)
  const [notice, setNotice] = useState(false)
  const returnFocus = useRef<HTMLElement | null>(null)
  const block = useRef<HTMLElement | null>(null)
  const addButton = useRef<HTMLButtonElement | null>(null)
  const data = resource.data
  const capabilities = data?.capabilities
  const actionable = capabilities?.can_change || capabilities?.can_delete

  function saved(item: Info) {
    resource.updateData((previous) => ({ ...previous, items: [...previous.items.filter((entry) => entry.id !== item.id), item].sort((a, b) => a.type.name.localeCompare(b.type.name) || a.id - b.id) }))
    setEditing(null)
    setNotice(true)
    void resource.refresh()
  }
  function deleted(id: number) {
    returnFocus.current = addButton.current ?? block.current
    resource.updateData((previous) => ({ ...previous, items: previous.items.filter((entry) => entry.id !== id) }))
    setDeleting(null)
    setSelected(null)
    setNotice(true)
    void resource.refresh()
  }
  return <section ref={block} tabIndex={-1} aria-label={t('genericInfo.section')} className={styles.block}>
    {resource.loading && <p role="status">{t('genericInfo.loading')}</p>}
    {!!resource.error && <Alert tone="danger">{t('employee.secondaryError')} <Button onClick={resource.retry} variant="ghost">{t('common.retry')}</Button></Alert>}
    {notice && !resource.refreshError && <span role="status" className="sr-only">{t('genericInfo.saved')}</span>}
    {!!resource.refreshError && <Alert tone="warning">{t('genericInfo.refreshFailed')} <Button disabled={resource.refreshing} onClick={() => void resource.refresh()} variant="ghost">{t('common.retry')}</Button></Alert>}
    {data && <>
      <dl className={styles.list}>
        {data.items.map((item) => {
          const Icon = genericInfoIcon(item.type.icon)
          return <div key={item.id} className={`${styles.row} ${selected === item.id ? styles.selected : ''}`} tabIndex={actionable ? 0 : undefined}
            onClick={actionable ? (event) => { if (!(event.target as HTMLElement).closest('button,a')) setSelected(item.id) } : undefined}
            onKeyDown={actionable ? (event) => { if (event.target === event.currentTarget && ['Enter', ' '].includes(event.key)) { event.preventDefault(); setSelected(item.id) } } : undefined}>
            <dt><Icon aria-hidden="true" size={16} />{item.type.name}</dt>
            <dd><span className={styles.value}><CopyableValue value={item.value} /></span>
            {actionable && <div className={styles.actions}><DropdownMenu onOpenChange={(open) => { if (open) setSelected(item.id) }}>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" />} aria-label={t('genericInfo.actions', { name: item.type.name })} onClick={(event) => { returnFocus.current = event.currentTarget }}><Ellipsis aria-hidden="true" /></DropdownMenuTrigger>
              <DropdownMenuContent align="end" finalFocus={() => editing || deleting ? false : true}>
                {capabilities?.can_change && <DropdownMenuItem onClick={() => setEditing(item)}><Pencil aria-hidden="true" />{t('genericInfo.edit')}</DropdownMenuItem>}
                {capabilities?.can_delete && <DropdownMenuItem onClick={() => setDeleting(item)}><Trash2 aria-hidden="true" />{t('genericInfo.delete')}</DropdownMenuItem>}
              </DropdownMenuContent>
            </DropdownMenu></div>}
            </dd>
          </div>
        })}
      </dl>
      {!data.items.length && <p className={styles.empty}>{t('employee.noGenericInfo')}</p>}
      {capabilities?.can_add && <Button ref={addButton} size="sm" variant="ghost" onClick={() => { returnFocus.current = addButton.current; setEditing('new') }}><Plus aria-hidden="true" />{t('genericInfo.add')}</Button>}
    </>}
    {editing && <GenericInfoFormSheet employeeId={employeeId} item={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={saved} returnFocus={returnFocus} />}
    {deleting && <DeleteInfo employeeId={employeeId} item={deleting} onCancel={() => setDeleting(null)} onDeleted={() => deleted(deleting.id)} returnFocus={returnFocus} />}
  </section>
}

function DeleteInfo({ employeeId, item, onCancel, onDeleted, returnFocus }: {
  employeeId: string; item: Info; onCancel: () => void; onDeleted: () => void; returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    const result = await mutation.run(() => deleteEmployeeGenericInfo(employeeId, item.id))
    if (result) onDeleted()
  }
  return <ConfirmDialog title={t('genericInfo.deleteTitle')} description={t('genericInfo.deleteDescription', { name: item.type.name })} pending={mutation.pending} onCancel={onCancel} onConfirm={() => void remove()} returnFocus={returnFocus}
    error={error && <Alert tone="danger">{error.messages.join(' ') || t(`genericInfo.error.${error.kind}`)}</Alert>} />
}
