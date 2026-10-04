import { StickyNote } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ContractHubItem, ContractHubOrdering } from '../api/contracts'
import { GenericNotes, type GenericNotesHandle } from '../components/GenericNotes'
import { ItemActionMenu } from '../components/ItemActionMenu'
import { SelectableTableRow } from '../components/SelectableTableRow'
import { SortableTableHeader } from '../components/SortableTableHeader'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Button } from '../ui/Button'
import { contractPercent } from './contractPresentation'
import contractStyles from './ContractSection.module.css'
import styles from './EmployeeListPage.module.css'

const dateLabel = (value: string | null, language: string) => value ? new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`)) : '—'
const moneyLabel = (value: string, language: string) => new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value))

type Props = {
  items: ContractHubItem[]
  selectedId: number | null
  onSelect: (id: number | null) => void
  onNotesClosed: () => void
  onEdit?: (item: ContractHubItem) => void
  onActionTrigger?: (element: HTMLElement) => void
  editingId?: number | null
  ordering?: ContractHubOrdering
  onSort?: (ordering: ContractHubOrdering) => void
}

export function ContractHubTable({ items, selectedId, onSelect, onNotesClosed, onEdit, onActionTrigger, editingId, ordering, onSort }: Props) {
  const { t, language } = useTranslation()
  const [notesFor, setNotesFor] = useState<ContractHubItem | null>(null)
  const notesHandle = useRef<GenericNotesHandle | null>(null)
  const notesTrigger = useRef<HTMLElement | null>(null)
  const closingNotes = useRef(false)

  async function closeNotes() {
    if (closingNotes.current) return
    closingNotes.current = true
    try {
      if (await notesHandle.current?.savePending() !== false) {
        setNotesFor(null)
        onNotesClosed()
      }
    } finally { closingNotes.current = false }
  }

  function header(label: string, field: ContractHubOrdering) {
    return ordering && onSort ? <SortableTableHeader label={label} field={field} ordering={ordering} onSort={(value) => onSort(value as ContractHubOrdering)} /> : <th scope="col">{label}</th>
  }

  return <>
    <div className={styles.scroll} role="region" aria-label={t('contractHub.table')} tabIndex={0}>
      <table className={styles.table}><thead><tr>
        {header(t('employee.identity'), 'employee__last_name')}
        {header(t('contracts.contractType'), 'contract_type__name')}
        {header(t('contractHub.status'), 'status')}
        <th scope="col">{t('contracts.followUp')}</th>
        {header(t('projectBudgets.startDate'), 'start_date')}
        {header(t('projectBudgets.endDate'), 'end_date')}
        <th scope="col">{t('employee.quotity')}</th>
        {header(t('employee.project'), 'fund__project__name')}
        <th scope="col">{t('contracts.reference')}</th>
        {header(t('contracts.total'), 'hub_total_amount')}
        <th scope="col"><span className="sr-only">{t('contracts.notes')}</span></th>
        <th scope="col"><span className="sr-only">{t('list.menu')}</span></th>
      </tr></thead><tbody>{items.map((item) => {
        const employee = `${item.employee.first_name} ${item.employee.last_name}`
        const project = item.fund.project
        return <SelectableTableRow key={item.id} rowId={item.id} selectedId={selectedId} onSelect={onSelect} aria-label={t('common.actionsFor', { name: employee })}>
          <th scope="row">{item.employee.can_view ? <Link to={`/employees/${item.employee.id}`}>{employee}</Link> : employee}</th>
          <td>{item.contract_type?.name ?? '—'}</td>
          <td>{t(item.status.code === 'effe' ? 'contracts.effective' : 'contracts.provisional')}</td>
          <td>{t(item.is_active ? 'filters.yes' : 'filters.no')}</td>
          <td className={styles.date}>{dateLabel(item.start_date, language)}</td>
          <td className={styles.date}>{dateLabel(item.end_date, language)}</td>
          <td>{contractPercent(item.quotity, language)}</td>
          <td>{project.can_view ? <Link to={`/projects/${project.id}`}>{project.name}</Link> : project.name}</td>
          <td>{item.fund.reference ?? '—'}</td>
          <td>{moneyLabel(item.total_amount, language)}</td>
          <td className={contractStyles.notes}>{(item.notes?.visible_count > 0 || item.notes?.can_add) && <Button variant="ghost" size="sm" aria-label={item.notes.visible_count > 0 ? `${t('contracts.openNotes')} · ${t(item.notes.visible_count === 1 ? 'contracts.oneNote' : 'contracts.manyNotes', { count: item.notes.visible_count })}` : t('contracts.openNotes')} onClick={(event) => { notesTrigger.current = event.currentTarget; setNotesFor(item) }}><StickyNote aria-hidden="true" />{item.notes.visible_count > 0 && <span>{item.notes.visible_count}</span>}</Button>}</td>
          <td className={styles.actions}><span className={styles.rowMenu}><ItemActionMenu label={t('common.actionsFor', { name: employee })} canChange={Boolean(onEdit && item.capabilities.can_change)} canDelete={false} adminUrl={item.admin_url} onOpen={() => onSelect(item.id)} onTrigger={onActionTrigger} finalFocus={() => editingId === item.id ? false : true} onEdit={() => onEdit?.(item)} onDelete={() => {}} /></span></td>
        </SelectableTableRow>
      })}</tbody></table>
    </div>
    {notesFor && <Sheet open onOpenChange={(open) => { if (!open) void closeNotes() }}><SheetContent finalFocus={notesTrigger}>
      <SheetHeader><SheetTitle>{t('contracts.notes')}</SheetTitle><SheetDescription>{notesFor.contract_type?.name ?? notesFor.fund.display_name}</SheetDescription></SheetHeader>
      <GenericNotes ref={notesHandle} scope="contract" objectId={String(notesFor.id)} />
      <div className={contractStyles.notesClose}><Button variant="secondary" onClick={() => void closeNotes()}>{t('common.close')}</Button></div>
    </SheetContent></Sheet>}
  </>
}
