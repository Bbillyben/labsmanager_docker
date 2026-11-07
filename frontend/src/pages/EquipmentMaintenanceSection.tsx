import { useCallback, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Ban, Check, Plus } from 'lucide-react';
import {
  actOnEquipmentMaintenance,
  createEquipmentMaintenance,
  deleteEquipmentMaintenance,
  equipmentMaintenanceExpenseOptions,
  getEquipmentMaintenance,
  listEquipmentMaintenances,
  updateEquipmentMaintenance,
  type EquipmentMaintenance,
  type MaintenanceStatus,
  type MaintenanceType,
  type MaintenanceWrite,
} from '../api/equipmentMaintenance';
import { normalizeMutationError } from '../api/errors';
import { useMutation } from '../api/useMutation';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { ItemActionMenu } from '../components/ItemActionMenu';
import { Input } from '../components/ui/input';
import { NativeSelect } from '../components/ui/native-select';
import { Textarea } from '../components/ui/textarea';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { StatusBadge } from '../ui/StatusBadge';
import { useEmployeeResource } from './useEmployeeResource';
import { localToday } from '../calendar/resourceVisibility';
import { EquipmentMaintenanceCalendarPage } from './EquipmentMaintenanceCalendarPage';
import listStyles from './EmployeeMilestones.module.css';
import panelStyles from './EmployeeDetailPage.module.css';
import formStyles from './ProjectOverview.module.css';

const types: MaintenanceType[] = ['preventive', 'corrective', 'inspection', 'calibration', 'other'];
const statuses: MaintenanceStatus[] = ['planned', 'in_progress', 'completed', 'cancelled'];
const today = localToday;

function initialWrite(item?: EquipmentMaintenance): MaintenanceWrite {
  return {
    title: item?.title ?? '',
    maintenance_type: item?.maintenance_type ?? 'preventive',
    status: item?.status ?? 'planned',
    scheduled_date: item?.scheduled_date ?? today(),
    scheduled_start_time: item?.scheduled_start_time?.slice(0, 5) ?? null,
    scheduled_end_time: item?.scheduled_end_time?.slice(0, 5) ?? null,
    performed_date: item?.performed_date ?? null,
    description: item?.description ?? '',
    report: item?.report ?? '',
    expense_link_id: item?.expense_link?.id ?? null,
  };
}

/** The Equipment page owns the list; the form never creates a financial Expense. */
export function EquipmentMaintenanceSection({ equipmentId }: { equipmentId: string }) {
  const { t } = useTranslation();
  const [query, setQuery] = useSearchParams();
  const offset = Math.max(0, Number(query.get('maintenanceOffset')) || 0);
  const status = query.get('maintenanceStatus') ?? '';
  const kind = query.get('maintenanceType') ?? '';
  const overdue = query.get('maintenanceOverdue') === '1';
  const params = new URLSearchParams({ limit: '25', offset: String(offset) });
  if (status) params.set('status', status);
  if (kind) params.set('maintenance_type', kind);
  if (overdue) params.set('overdue', '1');
  const loader = useCallback(
    (key: string, signal: AbortSignal) => listEquipmentMaintenances(equipmentId, key, signal),
    [equipmentId],
  );
  const resource = useEmployeeResource(params.toString(), loader);
  const selectedId = Number(query.get('maintenance'));
  const detailLoader = useCallback(
    (key: string, signal: AbortSignal) => getEquipmentMaintenance(Number(key), signal),
    [],
  );
  const detail = useEmployeeResource(String(selectedId), detailLoader, selectedId > 0);
  const [editing, setEditing] = useState<EquipmentMaintenance | 'new' | null>(null);
  const [mode, setMode] = useState<'list' | 'calendar'>('list');
  const [confirm, setConfirm] = useState<{
    item: EquipmentMaintenance;
    action: 'cancel' | 'delete';
  } | null>(null);
  const [performed, setPerformed] = useState<EquipmentMaintenance | null>(null);
  const [performedDate, setPerformedDate] = useState(today());
  const [report, setReport] = useState('');
  const mutation = useMutation();
  const focus = useRef<HTMLElement | null>(null);
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;

  function filter(name: string, value: string) {
    const next = new URLSearchParams(query);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete('maintenanceOffset');
    setQuery(next);
  }
  function page(nextOffset: number) {
    const next = new URLSearchParams(query);
    next.set('maintenanceOffset', String(nextOffset));
    setQuery(next);
  }
  function closeDetail() {
    const next = new URLSearchParams(query);
    next.delete('maintenance');
    setQuery(next);
  }
  async function change(action: () => Promise<unknown>) {
    const result = await mutation.run(action);
    if (result) {
      setEditing(null);
      setPerformed(null);
      setConfirm(null);
      await resource.refresh();
    }
  }

  const heading = (
    <div className={panelStyles.projectHeading}>
      <h2 className={panelStyles.panelTitle}>{t('equipmentMaintenance.title')}</h2>
      <div
        role="group"
        aria-label={t('equipmentMaintenance.view')}
      >
        <Button
          size="sm"
          variant={mode === 'list' ? 'secondary' : 'ghost'}
          aria-pressed={mode === 'list'}
          onClick={() => setMode('list')}
        >
          {t('gantt.list')}
        </Button>
        <Button
          size="sm"
          variant={mode === 'calendar' ? 'secondary' : 'ghost'}
          aria-pressed={mode === 'calendar'}
          onClick={() => setMode('calendar')}
        >
          {t('equipmentMaintenance.calendar')}
        </Button>
      </div>
    </div>
  );
  if (mode === 'calendar')
    return (
      <section aria-label={t('equipmentMaintenance.title')}>
        {heading}
        <EquipmentMaintenanceCalendarPage
          embedded
          onOpenMaintenance={(id) => {
            const next = new URLSearchParams(query);
            next.set('maintenance', String(id));
            setQuery(next);
            setMode('list');
          }}
        />
      </section>
    );
  if (resource.loading)
    return (
      <>
        <section aria-label={t('equipmentMaintenance.title')}>{heading}</section>
        <p role="status">{t('common.loading')}</p>
      </>
    );
  if (resource.error || !resource.data)
    return (
      <Alert tone="danger">
        {t('equipmentMaintenance.loadError')}{' '}
        <Button onClick={resource.retry}>{t('common.retry')}</Button>
      </Alert>
    );
  const data = resource.data;
  const groups = [
    [
      'overdue',
      data.results.filter(
        (item) =>
          item.status !== 'completed' &&
          item.status !== 'cancelled' &&
          item.scheduled_date < today(),
      ),
    ],
    [
      'in_progress',
      data.results.filter(
        (item) => item.status === 'in_progress' && item.scheduled_date >= today(),
      ),
    ],
    [
      'planned',
      data.results.filter((item) => item.status === 'planned' && item.scheduled_date >= today()),
    ],
    ['completed', data.results.filter((item) => item.status === 'completed')],
    ['cancelled', data.results.filter((item) => item.status === 'cancelled')],
  ] as const;
  return (
    <section
      aria-label={t('equipmentMaintenance.title')}
      className="grid gap-4"
    >
      {heading}
      <div className="flex flex-wrap items-center gap-2">
        {data.capabilities.can_add && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setEditing('new')}
          >
            <Plus aria-hidden="true" />
            {t('equipmentMaintenance.add')}
          </Button>
        )}
      </div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="grid gap-1 text-sm">
          {t('equipmentMaintenance.type')}{' '}
          <NativeSelect
            value={kind}
            onChange={(event) => filter('maintenanceType', event.target.value)}
          >
            <option value="">{t('equipmentMaintenance.all')}</option>
            {types.map((value) => (
              <option
                key={value}
                value={value}
              >
                {t(`equipmentMaintenance.type.${value}`)}
              </option>
            ))}
          </NativeSelect>
        </label>
        <label className="grid gap-1 text-sm">
          {t('equipmentMaintenance.status')}{' '}
          <NativeSelect
            value={status}
            onChange={(event) => filter('maintenanceStatus', event.target.value)}
          >
            <option value="">{t('equipmentMaintenance.all')}</option>
            {statuses.map((value) => (
              <option
                key={value}
                value={value}
              >
                {t(`equipmentMaintenance.status.${value}`)}
              </option>
            ))}
          </NativeSelect>
        </label>
        <label>
          <input
            type="checkbox"
            checked={overdue}
            onChange={(event) => filter('maintenanceOverdue', event.target.checked ? '1' : '')}
          />{' '}
          {t('equipmentMaintenance.overdue')}
        </label>
      </div>
      <div className={listStyles.groups}>
        {groups.map(
          ([name, items]) =>
            items.length > 0 && (
              <section
                key={name}
                className={listStyles.group}
                data-state={name}
              >
                <h3 className="border-b border-border px-1 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  {t(`equipmentMaintenance.status.${name}`)} · {items.length}
                </h3>
                <div className={listStyles.rows}>
                  {items.map((item) => (
                    <div
                      key={item.id}
                      id={`maintenance-${item.id}`}
                      className={listStyles.row}
                    >
                      <button
                        type="button"
                        className={listStyles.rowButton}
                        onClick={() => {
                          const next = new URLSearchParams(query);
                          next.set('maintenance', String(item.id));
                          setQuery(next);
                        }}
                      >
                        <span className={listStyles.main}>
                          <strong>{item.title}</strong>
                          <small>
                            {t(`equipmentMaintenance.type.${item.maintenance_type}`)} ·{' '}
                            {item.scheduled_date}
                            {item.scheduled_start_time
                              ? ` ${item.scheduled_start_time.slice(0, 5)}–${item.scheduled_end_time?.slice(0, 5)}`
                              : ''}
                          </small>
                        </span>
                        <span className={listStyles.due}>
                          <StatusBadge
                            tone={
                              item.status === 'completed'
                                ? 'success'
                                : item.status === 'cancelled'
                                  ? 'neutral'
                                  : name === 'overdue'
                                    ? 'danger'
                                    : 'warning'
                            }
                          >
                            {t(`equipmentMaintenance.status.${item.status}`)}
                          </StatusBadge>
                          {item.performed_date && <small>{item.performed_date}</small>}
                        </span>
                      </button>
                      {(item.capabilities.can_change || item.capabilities.can_delete) && (
                        <span className={listStyles.rowActions}>
                          <ItemActionMenu
                            label={t('common.actionsFor', { name: item.title })}
                            canChange={item.capabilities.can_change}
                            canDelete={item.capabilities.can_delete}
                            onEdit={() => setEditing(item)}
                            onDelete={() => setConfirm({ item, action: 'delete' })}
                            extraActions={
                              item.capabilities.can_change &&
                              item.status !== 'completed' &&
                              item.status !== 'cancelled'
                                ? [
                                    {
                                      label: t('equipmentMaintenance.complete'),
                                      icon: <Check aria-hidden="true" />,
                                      onSelect: () => {
                                        setPerformed(item);
                                        setPerformedDate(today());
                                        setReport(item.report);
                                      },
                                    },
                                    {
                                      label: t('equipmentMaintenance.cancel'),
                                      icon: <Ban aria-hidden="true" />,
                                      onSelect: () => setConfirm({ item, action: 'cancel' }),
                                    },
                                  ]
                                : []
                            }
                          />
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            ),
        )}
      </div>
      {!data.count && <p>{t('equipmentMaintenance.empty')}</p>}
      <div className="flex gap-2">
        {data.previous && (
          <Button
            variant="ghost"
            onClick={() => page(Math.max(0, offset - 25))}
          >
            {t('common.previous')}
          </Button>
        )}
        {data.next && (
          <Button
            variant="ghost"
            onClick={() => page(offset + 25)}
          >
            {t('common.next')}
          </Button>
        )}
      </div>
      {error && (
        <Alert tone="danger">
          {[...error.messages, ...Object.values(error.fields).flat()].join(' ')}
        </Alert>
      )}
      {selectedId > 0 && (
        <Sheet
          open
          onOpenChange={(open) => {
            if (!open) closeDetail();
          }}
        >
          <SheetContent>
            <SheetHeader>
              <SheetTitle>{detail.data?.title ?? t('equipmentMaintenance.title')}</SheetTitle>
              <SheetDescription>{detail.data?.scheduled_date ?? ''}</SheetDescription>
            </SheetHeader>
            {detail.loading && <p role="status">{t('common.loading')}</p>}
            {Boolean(detail.error) && (
              <Alert tone="danger">{t('equipmentMaintenance.loadError')}</Alert>
            )}
            {detail.data && (
              <div className="grid gap-3 text-sm">
                <p>
                  {t(`equipmentMaintenance.type.${detail.data.maintenance_type}`)} ·{' '}
                  {t(`equipmentMaintenance.status.${detail.data.status}`)}
                </p>
                {detail.data.description && <p>{detail.data.description}</p>}
                {detail.data.report && (
                  <p>
                    {t('equipmentMaintenance.report')}: {detail.data.report}
                  </p>
                )}
                {detail.data.expense_link && (
                  <Link to={`/equipment/${equipmentId}/expenses`}>
                    {t('equipmentMaintenance.expense')}: {detail.data.expense_link.label}
                  </Link>
                )}
              </div>
            )}
          </SheetContent>
        </Sheet>
      )}
      {editing && (
        <MaintenanceForm
          equipmentId={equipmentId}
          item={editing === 'new' ? undefined : editing}
          error={
            error ? [...error.messages, ...Object.values(error.fields).flat()].join(' ') : null
          }
          pending={mutation.pending}
          onClose={() => setEditing(null)}
          onSave={(value) =>
            void change(() =>
              editing === 'new'
                ? createEquipmentMaintenance(equipmentId, value)
                : updateEquipmentMaintenance(editing.id, value),
            )
          }
        />
      )}
      {performed && (
        <Sheet
          open
          onOpenChange={(open) => {
            if (!open) setPerformed(null);
          }}
        >
          <SheetContent finalFocus={focus}>
            <SheetHeader>
              <SheetTitle>{t('equipmentMaintenance.complete')}</SheetTitle>
              <SheetDescription>{performed.title}</SheetDescription>
            </SheetHeader>
            <form
              className={formStyles.form}
              onSubmit={(event) => {
                event.preventDefault();
                void change(() =>
                  actOnEquipmentMaintenance(performed.id, 'complete', {
                    performed_date: performedDate,
                    report,
                  }),
                );
              }}
            >
              <label>
                {t('equipmentMaintenance.performedDate')}
                <Input
                  type="date"
                  required
                  value={performedDate}
                  onChange={(event) => setPerformedDate(event.target.value)}
                />
              </label>
              <label>
                {t('equipmentMaintenance.report')}
                <Textarea
                  value={report}
                  onChange={(event) => setReport(event.target.value)}
                />
              </label>
              {error && (
                <Alert tone="danger">
                  {[...error.messages, ...Object.values(error.fields).flat()].join(' ')}
                </Alert>
              )}
              <div className={formStyles.formButtons}>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={mutation.pending}
                  onClick={() => setPerformed(null)}
                >
                  {t('common.cancel')}
                </Button>
                <Button
                  type="submit"
                  disabled={mutation.pending}
                >
                  {t('common.save')}
                </Button>
              </div>
            </form>
          </SheetContent>
        </Sheet>
      )}
      {confirm && (
        <ConfirmDialog
          title={t(
            confirm.action === 'delete'
              ? 'equipmentMaintenance.deleteTitle'
              : 'equipmentMaintenance.cancelTitle',
          )}
          description={confirm.item.title}
          confirmLabel={t('equipmentMaintenance.confirm')}
          pending={mutation.pending}
          error={
            error ? (
              <Alert tone="danger">
                {[...error.messages, ...Object.values(error.fields).flat()].join(' ')}
              </Alert>
            ) : undefined
          }
          returnFocus={focus}
          onCancel={() => setConfirm(null)}
          onConfirm={() =>
            void change(() =>
              confirm.action === 'delete'
                ? deleteEquipmentMaintenance(confirm.item.id)
                : actOnEquipmentMaintenance(confirm.item.id, 'cancel'),
            )
          }
        />
      )}
    </section>
  );
}

function MaintenanceForm({
  equipmentId,
  item,
  error,
  pending,
  onClose,
  onSave,
}: {
  equipmentId: string;
  item?: EquipmentMaintenance;
  error: string | null;
  pending: boolean;
  onClose: () => void;
  onSave: (value: MaintenanceWrite) => void;
}) {
  const { t } = useTranslation();
  const [value, setValue] = useState<MaintenanceWrite>(() => initialWrite(item));
  const loader = useCallback(
    (id: string, signal: AbortSignal) => equipmentMaintenanceExpenseOptions(id, signal),
    [],
  );
  const options = useEmployeeResource(equipmentId, loader);
  function field<K extends keyof MaintenanceWrite>(name: K, next: MaintenanceWrite[K]) {
    setValue((current) => ({ ...current, [name]: next }));
  }
  function submit(event: FormEvent) {
    event.preventDefault();
    if (item && !item.expense_link && value.expense_link_id === null) {
      const withoutLink = { ...value };
      delete withoutLink.expense_link_id;
      onSave(withoutLink);
    } else onSave(value);
  }
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open && !pending) onClose();
      }}
    >
      <SheetContent>
        <SheetHeader>
          <SheetTitle>
            {t(item ? 'equipmentMaintenance.edit' : 'equipmentMaintenance.add')}
          </SheetTitle>
          <SheetDescription>{t('equipmentMaintenance.formDescription')}</SheetDescription>
        </SheetHeader>
        <form
          className={`${formStyles.form} sm:grid-cols-2`}
          onSubmit={submit}
          aria-busy={pending}
        >
          {error && (
            <div className="sm:col-span-2">
              <Alert tone="danger">{error}</Alert>
            </div>
          )}
          <label className="sm:col-span-2">
            {t('equipmentMaintenance.name')}
            <Input
              required
              maxLength={200}
              value={value.title}
              disabled={pending}
              onChange={(event) => field('title', event.target.value)}
            />
          </label>
          <label>
            {t('equipmentMaintenance.type')}
            <NativeSelect
              className="w-full"
              value={value.maintenance_type}
              disabled={pending}
              onChange={(event) => field('maintenance_type', event.target.value as MaintenanceType)}
            >
              {types.map((type) => (
                <option
                  key={type}
                  value={type}
                >
                  {t(`equipmentMaintenance.type.${type}`)}
                </option>
              ))}
            </NativeSelect>
          </label>
          <label>
            {t('equipmentMaintenance.status')}
            <NativeSelect
              className="w-full"
              value={value.status}
              disabled={pending}
              onChange={(event) => field('status', event.target.value as MaintenanceStatus)}
            >
              {statuses.map((status) => (
                <option
                  key={status}
                  value={status}
                >
                  {t(`equipmentMaintenance.status.${status}`)}
                </option>
              ))}
            </NativeSelect>
          </label>
          <label className="sm:col-span-2">
            {t('equipmentMaintenance.scheduledDate')}
            <Input
              type="date"
              required
              value={value.scheduled_date}
              disabled={pending}
              onChange={(event) => field('scheduled_date', event.target.value)}
            />
          </label>
          <label>
            {t('equipmentMaintenance.startTime')}
            <Input
              type="time"
              value={value.scheduled_start_time ?? ''}
              disabled={pending}
              onChange={(event) => field('scheduled_start_time', event.target.value || null)}
            />
          </label>
          <label>
            {t('equipmentMaintenance.endTime')}
            <Input
              type="time"
              value={value.scheduled_end_time ?? ''}
              disabled={pending}
              onChange={(event) => field('scheduled_end_time', event.target.value || null)}
            />
          </label>
          {value.status === 'completed' && (
            <label className="sm:col-span-2">
              {t('equipmentMaintenance.performedDate')}
              <Input
                type="date"
                required
                value={value.performed_date ?? ''}
                disabled={pending}
                onChange={(event) => field('performed_date', event.target.value || null)}
              />
            </label>
          )}
          <label className="sm:col-span-2">
            {t('equipmentMaintenance.description')}
            <Textarea
              value={value.description}
              disabled={pending}
              onChange={(event) => field('description', event.target.value)}
            />
          </label>
          {(options.data?.length || item?.expense_link) && (
            <label className="sm:col-span-2">
              {t('equipmentMaintenance.expense')}
              <NativeSelect
                className="w-full"
                value={value.expense_link_id ?? ''}
                disabled={pending}
                onChange={(event) =>
                  field('expense_link_id', event.target.value ? Number(event.target.value) : null)
                }
              >
                <option value="">{t('equipmentMaintenance.noExpense')}</option>
                {options.data?.map((option) => (
                  <option
                    key={option.id}
                    value={option.id}
                  >
                    {option.label}
                  </option>
                ))}
                {Boolean(item?.expense_link) &&
                  !options.data?.some((option) => option.id === item?.expense_link?.id) && (
                    <option value={item?.expense_link?.id}>{item?.expense_link?.label}</option>
                  )}
              </NativeSelect>
            </label>
          )}
          {(item || value.status === 'completed') && (
            <label className="sm:col-span-2">
              {t('equipmentMaintenance.report')}
              <Textarea
                value={value.report}
                disabled={pending}
                onChange={(event) => field('report', event.target.value)}
              />
            </label>
          )}
          {Boolean(options.error) && (
            <div className="sm:col-span-2">
              <Alert tone="warning">
                {t('equipmentMaintenance.expenseOptionsError')}{' '}
                <Button
                  type="button"
                  variant="ghost"
                  onClick={options.retry}
                >
                  {t('common.retry')}
                </Button>
              </Alert>
            </div>
          )}
          <div className={`${formStyles.formButtons} sm:col-span-2`}>
            <Button
              type="button"
              variant="ghost"
              disabled={pending}
              onClick={onClose}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={pending}
            >
              {t('common.save')}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
