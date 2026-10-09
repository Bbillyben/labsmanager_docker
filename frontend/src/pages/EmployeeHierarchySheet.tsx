import { useMemo, useState, type FormEvent, type RefObject } from 'react'
import { addEmployeeHierarchyRelation, getEmployee, getEmployeeHierarchyCandidates, updateEmployeeHierarchyRelation,
  type EmployeeHierarchyDates, type EmployeeHierarchyDirection, type EmployeeHierarchyRelation } from '../api/employees'
import { ApiError, normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { EntitySearch } from '../filters/EntitySearch'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

export function EmployeeHierarchySheet({ employeeId, direction, relation, defaultDates, onClose, onSaved, returnFocus }: {
  employeeId: string
  direction: EmployeeHierarchyDirection
  relation: EmployeeHierarchyRelation | null
  defaultDates: EmployeeHierarchyDates
  onClose: () => void
  onSaved: () => void
  returnFocus: RefObject<HTMLElement | null>
}) {
  const { t } = useTranslation()
  const [linkedId, setLinkedId] = useState(relation ? String(relation.employee.id) : '')
  const [dates, setDates] = useState<EmployeeHierarchyDates>(relation
    ? { start_date: relation.start_date, end_date: relation.end_date } : defaultDates)
  const source = useMemo(() => ({
    async search(query: string, signal: AbortSignal) {
      const response = await getEmployeeHierarchyCandidates(employeeId, direction, query, signal)
      return { options: response.results.map((item) => ({ value: String(item.id), label: item.name })), hasMore: response.has_more }
    },
    async resolve(id: string, signal: AbortSignal) {
      try {
        const employee = await getEmployee(id, signal)
        return { value: id, label: `${employee.first_name} ${employee.last_name}` }
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null
        throw error
      }
    },
  }), [employeeId, direction])
  const mutation = useMutation()
  const error = mutation.error ? normalizeMutationError(mutation.error) : null
  const errorText = (value: string) => {
    if (value === 'self_relation') return t('employee.hierarchyError.self_relation')
    if (value === 'duplicate') return t('employee.hierarchyError.duplicate')
    if (value === 'cycle') return t('employee.hierarchyError.cycle')
    if (value === 'end_before_start') return t('employee.hierarchyError.end_before_start')
    return value
  }
  const fieldError = (field: string) => error?.fields[field]?.map(errorText).join(' ')
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!relation && !linkedId) return
    const result = await mutation.run(() => relation
      ? updateEmployeeHierarchyRelation(employeeId, relation.id, dates)
      : addEmployeeHierarchyRelation(employeeId, direction, Number(linkedId), dates))
    if (result) onSaved()
  }
  const title = t(relation ? direction === 'superior' ? 'employee.editSuperior' : 'employee.editSubordinate'
    : direction === 'superior' ? 'employee.addSuperior' : 'employee.addSubordinate')
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{title}</SheetTitle><SheetDescription>{t('employee.hierarchyDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}>
      {error && (error.messages.length > 0 || Object.keys(error.fields).some((field) => !['employee_id', 'start_date', 'end_date'].includes(field))) &&
        <Alert tone="danger">{[...error.messages, ...Object.entries(error.fields).filter(([field]) => !['employee_id', 'start_date', 'end_date'].includes(field)).flatMap(([, messages]) => messages)].map(errorText).join(' ') || t('employee.hierarchySaveError')}</Alert>}
      {relation ? <p>{t('employee.selectEmployee')}: <strong>{relation.employee.first_name} {relation.employee.last_name}</strong></p>
        : <label className="grid gap-1">{t('employee.selectEmployee')}<EntitySearch id="hierarchy-employee" label={t('employee.selectEmployee')} value={linkedId} source={source} onChange={setLinkedId} />{fieldError('employee_id') && <span role="alert" className="text-sm text-destructive">{fieldError('employee_id')}</span>}</label>}
      <label className="grid gap-1">{t('team.startDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={dates.start_date ?? ''} onChange={(event) => setDates((current) => ({ ...current, start_date: event.target.value || null }))} />{fieldError('start_date') && <span role="alert" className="text-sm text-destructive">{fieldError('start_date')}</span>}</label>
      <label className="grid gap-1">{t('team.endDate')}<input className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm" type="date" value={dates.end_date ?? ''} onChange={(event) => setDates((current) => ({ ...current, end_date: event.target.value || null }))} />{fieldError('end_date') && <span role="alert" className="text-sm text-destructive">{fieldError('end_date')}</span>}</label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || (!relation && !linkedId)}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
