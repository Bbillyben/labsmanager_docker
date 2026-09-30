import { useRef, useState, type RefObject } from 'react'
import { Plus } from 'lucide-react'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import { CopyableValue } from '../components/common/CopyableValue'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { useSelectableItem } from '../components/useSelectableItem'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { GenericInfoFormSheet } from './GenericInfoFormSheet'
import { genericInfoIcon } from './genericInfoIcons'
import type { GenericInfoApi, GenericInfoCollection, GenericInfoItem } from './genericInfoContext'
import styles from './EmployeeGenericInfo.module.css'

type Props = {
  data: GenericInfoCollection | null
  loading?: boolean
  error?: unknown
  retry?: () => void
  refreshing?: boolean
  refreshError?: unknown
  refresh: () => Promise<boolean>
  update: (change: (data: GenericInfoCollection) => GenericInfoCollection) => void
  api: GenericInfoApi
}

export function GenericInfoSection({ data, loading, error, retry, refreshing, refreshError, refresh, update, api }: Props) {
  const { t } = useTranslation()
  const { selectedId, setSelectedId, containerRef, rowProps } = useSelectableItem()
  const [editing, setEditing] = useState<GenericInfoItem | 'new' | null>(null)
  const [deleting, setDeleting] = useState<GenericInfoItem | null>(null)
  const [notice, setNotice] = useState(false)
  const returnFocus = useRef<HTMLElement | null>(null)
  const addButton = useRef<HTMLButtonElement | null>(null)
  const capabilities = data?.capabilities
  const actionable = capabilities?.can_change || capabilities?.can_delete

  function saved(item: GenericInfoItem) {
    update((previous) => ({ ...previous, items: [...previous.items.filter((entry) => entry.id !== item.id), item].sort((a, b) => a.type.name.localeCompare(b.type.name) || a.id - b.id) }))
    setEditing(null)
    setNotice(true)
    void refresh()
  }
  function deleted(id: number) {
    returnFocus.current = addButton.current ?? containerRef.current
    update((previous) => ({ ...previous, items: previous.items.filter((entry) => entry.id !== id) }))
    setDeleting(null)
    setSelectedId(null)
    setNotice(true)
    void refresh()
  }
  return <section ref={containerRef} tabIndex={-1} aria-label={t('genericInfo.section')} className={styles.block}>
    {loading && <p role="status">{t('genericInfo.loading')}</p>}
    {!!error && <Alert tone="danger">{t('employee.secondaryError')} {retry && <Button onClick={retry} variant="ghost">{t('common.retry')}</Button>}</Alert>}
    {notice && !refreshError && <span role="status" className="sr-only">{t('genericInfo.saved')}</span>}
    {!!refreshError && <Alert tone="warning">{t('genericInfo.refreshFailed')} <Button disabled={refreshing} onClick={() => void refresh()} variant="ghost">{t('common.retry')}</Button></Alert>}
    {data && <>
      <dl className={styles.list}>
        {data.items.map((item) => {
          const Icon = genericInfoIcon(item.type.icon)
          return <div key={item.id} className={`${styles.row} ${selectedId === item.id ? styles.selected : ''}`} {...rowProps(item.id, !!actionable)}>
            <dt><Icon aria-hidden="true" size={16} />{item.type.name}</dt>
            <dd><span className={styles.value}><CopyableValue value={item.value} /></span>
              {actionable && <div className={styles.actions}><ItemActionMenu
                label={t('genericInfo.actions', { name: item.type.name })}
                canChange={!!capabilities?.can_change} canDelete={!!capabilities?.can_delete}
                onOpen={() => setSelectedId(item.id)}
                onTrigger={(trigger) => { returnFocus.current = trigger }}
                finalFocus={() => editing || deleting ? false : true}
                onEdit={() => setEditing(item)} onDelete={() => setDeleting(item)}
              /></div>}
            </dd>
          </div>
        })}
      </dl>
      {!data.items.length && <p className={styles.empty}>{t('employee.noGenericInfo')}</p>}
      {capabilities?.can_add && <Button ref={addButton} size="sm" variant="ghost" onClick={() => { returnFocus.current = addButton.current; setEditing('new') }}><Plus aria-hidden="true" />{t('genericInfo.add')}</Button>}
    </>}
    {editing && <GenericInfoFormSheet api={api} item={editing === 'new' ? null : editing} onClose={() => setEditing(null)} onSaved={saved} returnFocus={returnFocus} />}
    {deleting && <DeleteInfo api={api} item={deleting} onCancel={() => setDeleting(null)} onDeleted={() => deleted(deleting.id)} returnFocus={returnFocus} />}
  </section>
}

function DeleteInfo({ api, item, onCancel, onDeleted, returnFocus }: {
  api: GenericInfoApi; item: GenericInfoItem; onCancel: () => void; onDeleted: () => void; returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  async function remove() {
    const result = await mutation.run(() => api.delete(item.id))
    if (result) onDeleted()
  }
  return <ConfirmDialog title={t('genericInfo.deleteTitle')} description={t('genericInfo.deleteDescription', { name: item.type.name })} pending={mutation.pending} onCancel={onCancel} onConfirm={() => void remove()} returnFocus={returnFocus}
    error={error && <Alert tone="danger">{error.messages.join(' ') || t(`genericInfo.error.${error.kind}`)}</Alert>} />
}
