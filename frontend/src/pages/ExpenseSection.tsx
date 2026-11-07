import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Link2, Plus } from 'lucide-react';
import {
  createExpense,
  deleteExpense,
  deleteEquipmentExpense,
  getExpenseOptions,
  getExpenses,
  syncExpenses,
  updateExpense,
  type Expense,
  type ExpenseFilters,
  type ExpenseOptions,
  type ExpenseScope,
  type ExpenseWrite,
  type EquipmentExpenseNature,
} from '../api/expenses';
import { normalizeMutationError } from '../api/errors';
import { useMutation } from '../api/useMutation';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { ItemActionMenu } from '../components/ItemActionMenu';
import { EntityActionMenu } from '../components/EntityActionMenu';
import { SelectableTableRow } from '../components/SelectableTableRow';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { NativeSelect } from '../components/ui/native-select';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { useTranslation } from '../i18n/i18n';
import { ExpenseBusinessAssignments } from './ExpenseBusinessAssignments';
import { useEmployeeResource } from './useEmployeeResource';
import styles from './ExpenseSection.module.css';

const initialFilters: ExpenseFilters = {
  search: '',
  type: '',
  date_from: '',
  date_to: '',
  page: 1,
};
const dateLabel = (value: string, language: string) =>
  new Intl.DateTimeFormat(language, { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00Z`),
  );
const amountLabel = (value: string, language: string) =>
  new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(Number(value));

export function ExpenseReadOnlyDetails({
  item,
}: {
  item: Pick<Expense, 'expense_id' | 'desc' | 'date' | 'type' | 'amount' | 'status'>;
}) {
  const { t, language } = useTranslation();
  return (
    <dl className={styles.details}>
      <div>
        <dt>{t('expenses.reference')}</dt>
        <dd>{item.expense_id || '—'}</dd>
      </div>
      <div>
        <dt>{t('expenses.description')}</dt>
        <dd>{item.desc || '—'}</dd>
      </div>
      <div>
        <dt>{t('expenses.date')}</dt>
        <dd>{dateLabel(item.date, language)}</dd>
      </div>
      <div>
        <dt>{t('funding.costType')}</dt>
        <dd>{item.type.name}</dd>
      </div>
      <div>
        <dt>{t('expenses.status')}</dt>
        <dd>{t(`expenses.status.${item.status}`)}</dd>
      </div>
      <div>
        <dt>{t('funding.amount')}</dt>
        <dd>{amountLabel(item.amount, language)}</dd>
      </div>
    </dl>
  );
}

/** List Expenses for the selected funding context and expose permitted actions. */
export function ExpenseSection({
  scope,
  onFinancialChange,
  title,
}: {
  scope: ExpenseScope;
  onFinancialChange?: () => void | Promise<unknown>;
  title?: string;
}) {
  const { t, language } = useTranslation();
  const sectionTitle = title ?? t('expenses.title');
  const [filters, setFilters] = useState(initialFilters);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editing, setEditing] = useState<Expense | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Expense | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [assigning, setAssigning] = useState<Expense | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const section = useRef<HTMLElement | null>(null);
  const [focusVersion, setFocusVersion] = useState(0);
  const scopeKey =
    'equipmentId' in scope
      ? `equipment:${scope.equipmentId}`
      : 'hubContractId' in scope
        ? `hub-contract:${scope.hubContractId}`
        : 'budgetId' in scope
          ? `budget:${scope.projectId}:${scope.budgetId}`
          : 'fundId' in scope
            ? `fund:${scope.fundId}`
            : 'projectId' in scope
              ? `project-contract:${scope.projectId}:${scope.contractId}`
              : `contract:${scope.employeeId}:${scope.contractId}`;
  const filterKey = JSON.stringify(filters);
  const loader = useCallback(
    (_id: string, signal: AbortSignal) => getExpenses(scope, filters, signal),
    [scope, filters],
  );
  const optionsLoader = useCallback(
    (_id: string, signal: AbortSignal) => getExpenseOptions(scope, signal),
    [scope],
  );
  const resource = useEmployeeResource(`${scopeKey}:${filterKey}`, loader);
  const options = useEmployeeResource(scopeKey, optionsLoader);
  const [syncError, setSyncError] = useState<unknown>(null);
  useEffect(() => {
    if (!focusVersion) return;
    const timer = window.setTimeout(() => section.current?.focus(), 0);
    return () => window.clearTimeout(timer);
  }, [focusVersion]);

  async function changed() {
    setEditing(null);
    setDeleting(null);
    const refreshed = await resource.refresh();
    if (!refreshed) setSyncError(new Error(t('expenses.refreshError')));
    await onFinancialChange?.();
  }
  function setFilter(key: keyof ExpenseFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value, page: 1 }));
  }
  const data = resource.data;
  const pageCount = data ? Math.max(1, Math.ceil(data.count / 20)) : 1;
  return (
    <section
      ref={section}
      tabIndex={-1}
      className={styles.section}
      aria-label={sectionTitle}
    >
      <div className={styles.heading}>
        <h3>{sectionTitle}</h3>
        <div className={styles.buttons}>
          {data?.capabilities.can_sync_expenses && 'fundId' in scope && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(event) => {
                trigger.current = event.currentTarget;
                setSyncing(true);
              }}
            >
              {t('expenses.sync')}
            </Button>
          )}
          {data?.capabilities.can_add && (
            <Button
              size="sm"
              variant="secondary"
              onClick={(event) => {
                trigger.current = event.currentTarget;
                setEditing('new');
              }}
            >
              <Plus aria-hidden="true" />
              {t('expenses.add')}
            </Button>
          )}
        </div>
      </div>
      <div className={styles.filters}>
        <label>
          {t('expenses.search')}
          <input
            value={filters.search}
            onChange={(event) => setFilter('search', event.target.value)}
          />
        </label>
        <label>
          {t('funding.costType')}
          <NativeSelect
            value={filters.type}
            onChange={(event) => setFilter('type', event.target.value)}
          >
            <option value="">{t('expenses.allTypes')}</option>
            {options.data?.cost_types.map((entry) => (
              <option
                key={entry.id}
                value={entry.id}
              >
                {entry.name}
              </option>
            ))}
          </NativeSelect>
        </label>
        <label>
          {t('expenses.dateFrom')}
          <input
            type="date"
            value={filters.date_from}
            onChange={(event) => setFilter('date_from', event.target.value)}
          />
        </label>
        <label>
          {t('expenses.dateTo')}
          <input
            type="date"
            value={filters.date_to}
            onChange={(event) => setFilter('date_to', event.target.value)}
          />
        </label>
      </div>
      {resource.loading && <p role="status">{t('expenses.loading')}</p>}
      {Boolean(resource.error) && (
        <Alert tone="danger">
          {t('expenses.loadError')}{' '}
          <Button
            variant="ghost"
            onClick={resource.retry}
          >
            {t('common.retry')}
          </Button>
        </Alert>
      )}
      {(Boolean(resource.refreshError) || Boolean(syncError)) && (
        <Alert tone="warning">
          {t('expenses.refreshError')}{' '}
          <Button
            variant="ghost"
            onClick={() => {
              setSyncError(null);
              void resource.refresh();
              void onFinancialChange?.();
            }}
          >
            {t('common.retry')}
          </Button>
        </Alert>
      )}
      {data &&
        (data.results.length ? (
          <div className={styles.scroll}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{t('expenses.date')}</th>
                  {'equipmentId' in scope && <th>{t('equipmentExpenses.fund')}</th>}
                  <th>{t('expenses.reference')}</th>
                  <th>{t('expenses.description')}</th>
                  <th>{t('funding.costType')}</th>
                  <th>{t('expenses.status')}</th>
                  <th>{t('expenses.contract')}</th>
                  <th>{t('expenses.budget')}</th>
                  <th>{t('funding.amount')}</th>
                  {'equipmentId' in scope && <th>{t('equipmentExpenses.nature')}</th>}
                  <th>
                    <span className="sr-only">{t('list.menu')}</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((item) => (
                  <SelectableTableRow
                    key={item.id}
                    id={`expense-row-${item.id}`}
                    rowId={item.id}
                    selectedId={selectedId}
                    onSelect={setSelectedId}
                  >
                    <td>{dateLabel(item.date, language)}</td>
                    {'equipmentId' in scope && <td>{item.fund?.name ?? '—'}</td>}
                    <td>{item.expense_id || '—'}</td>
                    <td>{item.desc || '—'}</td>
                    <td>{item.type.name}</td>
                    <td>{t(`expenses.status.${item.status}`)}</td>
                    <td>{item.contract?.name || '—'}</td>
                    <td>{item.budget?.name || '—'}</td>
                    <td className={styles.number}>{amountLabel(item.amount, language)}</td>
                    {'equipmentId' in scope && (
                      <td>{item.nature ? t(`equipmentExpenses.${item.nature}`) : '—'}</td>
                    )}
                    <td className={styles.actions}>
                      {'equipmentId' in scope ? (
                        <EntityActionMenu
                          label={t('common.actionsFor', {
                            name: item.expense_id || item.desc || item.type.name,
                          })}
                          groups={[
                            [
                              ...(item.capabilities.can_change
                                ? [
                                    {
                                      id: 'edit',
                                      label: t('common.edit'),
                                      onSelect: () => setEditing(item),
                                    },
                                  ]
                                : []),
                              ...(item.can_view_business_assignments
                                ? [
                                    {
                                      id: 'assignments',
                                      label: t('expenseAssignments.action'),
                                      onSelect: () => setAssigning(item),
                                    },
                                  ]
                                : []),
                              ...(item.capabilities.can_delete
                                ? [
                                    {
                                      id: 'delete',
                                      label: t('equipmentExpenses.delete'),
                                      onSelect: () => setDeleting(item),
                                    },
                                  ]
                                : []),
                            ],
                          ]}
                          onTrigger={(element) => {
                            trigger.current = element;
                          }}
                          finalFocus={() => (editing || assigning || deleting ? false : true)}
                        />
                      ) : (
                        <ItemActionMenu
                          label={t('common.actionsFor', {
                            name: item.expense_id || item.desc || item.type.name,
                          })}
                          canChange={item.capabilities.can_change}
                          canDelete={item.capabilities.can_delete}
                          adminUrl={item.admin_url}
                          onOpen={() => setSelectedId(item.id)}
                          onTrigger={(element) => {
                            trigger.current = element;
                          }}
                          finalFocus={() => (editing || deleting ? false : true)}
                          onEdit={() => setEditing(item)}
                          onDelete={() => setDeleting(item)}
                          extraAction={
                            item.can_view_business_assignments
                              ? {
                                  label: t('expenseAssignments.action'),
                                  icon: <Link2 aria-hidden="true" />,
                                  onSelect: () => setAssigning(item),
                                }
                              : undefined
                          }
                        />
                      )}
                    </td>
                  </SelectableTableRow>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p>{t('expenses.empty')}</p>
        ))}
      {data && pageCount > 1 && (
        <nav
          className={styles.pagination}
          aria-label={t('expenses.pagination')}
        >
          <Button
            variant="ghost"
            disabled={!data.previous}
            onClick={() => setFilters((value) => ({ ...value, page: value.page - 1 }))}
          >
            {t('common.previous')}
          </Button>
          <span>{t('expenses.page', { page: filters.page, pages: pageCount })}</span>
          <Button
            variant="ghost"
            disabled={!data.next}
            onClick={() => setFilters((value) => ({ ...value, page: value.page + 1 }))}
          >
            {t('common.next')}
          </Button>
        </nav>
      )}
      {'equipmentId' in scope && data?.total_visible !== undefined && (
        <p className="text-sm text-muted-foreground">
          {t('equipmentExpenses.visibleTotal')}: {amountLabel(data.total_visible, language)}
        </p>
      )}
      {editing && (
        <ExpenseSheet
          scope={scope}
          mode={data?.capabilities.expense_mode ?? 's'}
          item={editing === 'new' ? null : editing}
          options={options.data}
          optionsError={Boolean(options.error)}
          retryOptions={options.retry}
          returnFocus={trigger}
          onClose={() => setEditing(null)}
          onSaved={() => void changed()}
        />
      )}
      {deleting && (
        <ExpenseConfirmation
          title={t('expenses.deleteTitle')}
          description={t('expenses.deleteDescription', {
            name: deleting.expense_id || deleting.desc || deleting.type.name,
          })}
          returnFocus={trigger}
          onCancel={() => setDeleting(null)}
          onConfirm={() =>
            'equipmentId' in scope
              ? deleteEquipmentExpense(scope.equipmentId, deleting.id)
              : deleteExpense(scope, deleting.id)
          }
          onDone={() => {
            trigger.current = section.current;
            setSelectedId(null);
            setFocusVersion((v) => v + 1);
            void changed();
          }}
        />
      )}
      {assigning && (
        <ExpenseBusinessAssignments
          expenseId={assigning.id}
          returnFocus={trigger}
          onClose={() => setAssigning(null)}
          onChanged={() => void changed()}
        />
      )}
      {syncing && scope.fundId !== undefined && (
        <ExpenseConfirmation
          title={t('expenses.syncTitle')}
          description={t('expenses.syncDescription')}
          confirmLabel={t('expenses.sync')}
          returnFocus={trigger}
          onCancel={() => setSyncing(false)}
          onConfirm={() => syncExpenses(scope.fundId!)}
          onDone={() => {
            setSyncing(false);
            void changed();
          }}
        />
      )}
    </section>
  );
}

/** Edit an Expense while preserving its Fund and Contract context. */
function ExpenseSheet({
  scope,
  mode,
  item,
  options,
  optionsError,
  retryOptions,
  returnFocus,
  onClose,
  onSaved,
}: {
  scope: ExpenseScope;
  mode: 's' | 'e' | 'h';
  item: Expense | null;
  options: ExpenseOptions | null;
  optionsError: boolean;
  retryOptions: () => void;
  returnFocus: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<ExpenseWrite>({
    expense_id: item?.expense_id ?? '',
    desc: item?.desc ?? '',
    date: item?.date ?? new Date().toISOString().slice(0, 10),
    type_id: item?.type.id,
    amount: item?.amount ?? '',
    status: item?.status ?? 'r',
    contract_id:
      item?.contract?.id ??
      ('hubContractId' in scope ? scope.hubContractId : scope.contractId) ??
      null,
    budget_id: scope.budgetId ?? item?.budget?.id ?? null,
    ...('equipmentId' in scope
      ? { fund_id: item?.fund?.id, nature: item?.nature ?? ('other' as EquipmentExpenseNature) }
      : {}),
  });
  const mutation = useMutation();
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;
  const set = <K extends keyof ExpenseWrite>(key: K, value: ExpenseWrite[K]) =>
    setDraft((previous) => ({ ...previous, [key]: value }));
  async function save(event: FormEvent) {
    event.preventDefault();
    const financialDraft = { ...draft };
    if ('equipmentId' in scope && item) {
      delete financialDraft.fund_id;
      delete financialDraft.nature;
    }
    const result = await mutation.run(() =>
      item ? updateExpense(scope, item.id, financialDraft) : createExpense(scope, financialDraft),
    );
    if (result) onSaved();
  }
  const modeForFund =
    'equipmentId' in scope
      ? (options?.funds?.find((fund) => fund.id === draft.fund_id)?.expense_mode ?? 's')
      : mode;
  const typeChoices = draft.contract_id
    ? options?.cost_types.filter((entry) => options.hr_type_ids.includes(entry.id))
    : options?.cost_types;
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open && !mutation.pending) onClose();
      }}
    >
      <SheetContent finalFocus={returnFocus}>
        <SheetHeader>
          <SheetTitle>{t(item ? 'expenses.edit' : 'expenses.add')}</SheetTitle>
          <SheetDescription>{t('expenses.formDescription')}</SheetDescription>
        </SheetHeader>
        <form
          className={styles.form}
          onSubmit={(event) => void save(event)}
          aria-busy={mutation.pending}
        >
          {error && (
            <Alert tone="danger">
              {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
                t('expenses.saveError')}
            </Alert>
          )}
          {optionsError && (
            <Alert tone="danger">
              {t('expenses.optionsError')}{' '}
              <Button
                variant="ghost"
                onClick={retryOptions}
              >
                {t('common.retry')}
              </Button>
            </Alert>
          )}
          {'equipmentId' in scope && !item && (
            <>
              <label>
                {t('equipmentExpenses.fund')}
                <NativeSelect
                  required
                  value={draft.fund_id ?? ''}
                  disabled={!options}
                  onChange={(event) =>
                    setDraft((value) => ({
                      ...value,
                      fund_id: Number(event.target.value) || undefined,
                      contract_id: null,
                      budget_id: null,
                    }))
                  }
                >
                  <option value="">{t('common.choose')}</option>
                  {options?.funds?.map((fund) => (
                    <option
                      key={fund.id}
                      value={fund.id}
                    >
                      {fund.name}
                    </option>
                  ))}
                </NativeSelect>
              </label>
              <label>
                {t('equipmentExpenses.nature')}
                <NativeSelect
                  value={draft.nature ?? 'other'}
                  onChange={(event) => set('nature', event.target.value as EquipmentExpenseNature)}
                >
                  {(['purchase', 'maintenance', 'repair', 'other'] as const).map((nature) => (
                    <option
                      key={nature}
                      value={nature}
                    >
                      {t(`equipmentExpenses.${nature}`)}
                    </option>
                  ))}
                </NativeSelect>
              </label>
            </>
          )}
          <label>
            {t('expenses.reference')}
            <input
              value={draft.expense_id}
              onChange={(event) => set('expense_id', event.target.value)}
            />
          </label>
          <label>
            {t('expenses.description')}
            <input
              value={draft.desc}
              onChange={(event) => set('desc', event.target.value)}
            />
          </label>
          <label>
            {t('expenses.date')}
            <input
              required
              type="date"
              value={draft.date}
              onChange={(event) => set('date', event.target.value)}
            />
          </label>
          <label>
            {t('funding.costType')}
            <NativeSelect
              required
              value={draft.type_id ?? ''}
              disabled={!options}
              onChange={(event) => set('type_id', Number(event.target.value))}
            >
              <option value="">{t('common.choose')}</option>
              {typeChoices?.map((entry) => (
                <option
                  key={entry.id}
                  value={entry.id}
                >
                  {entry.name}
                </option>
              ))}
              {draft.type_id && !typeChoices?.some((entry) => entry.id === draft.type_id) && (
                <option value={draft.type_id}>{item?.type.name}</option>
              )}
            </NativeSelect>
          </label>
          <label>
            {t('expenses.status')}
            <NativeSelect
              value={draft.status}
              onChange={(event) => set('status', event.target.value as Expense['status'])}
            >
              {(['e', 'r', 'p'] as const).map((status) => (
                <option
                  key={status}
                  value={status}
                >
                  {t(`expenses.status.${status}`)}
                </option>
              ))}
            </NativeSelect>
          </label>
          <label>
            {t('funding.amount')}
            <input
              required
              type="number"
              step="0.01"
              value={draft.amount}
              onChange={(event) => set('amount', event.target.value)}
            />
          </label>
          <label>
            {t('expenses.contract')}
            <NativeSelect
              value={draft.contract_id ?? ''}
              disabled={!options || 'contractId' in scope || 'hubContractId' in scope}
              onChange={(event) =>
                set('contract_id', event.target.value ? Number(event.target.value) : null)
              }
            >
              <option value="">{t('expenses.noContract')}</option>
              {options?.contracts
                .filter((entry) => !('equipmentId' in scope) || entry.fund_id === draft.fund_id)
                .map((entry) => (
                  <option
                    key={entry.id}
                    value={entry.id}
                  >
                    {entry.name}
                  </option>
                ))}
            </NativeSelect>
          </label>
          <label>
            {t('expenses.budget')}
            <NativeSelect
              value={draft.budget_id ?? ''}
              disabled={!options || 'budgetId' in scope}
              onChange={(event) =>
                set('budget_id', event.target.value ? Number(event.target.value) : null)
              }
            >
              <option value="">{t('expenses.noBudget')}</option>
              {options?.budgets
                .filter((entry) => !('equipmentId' in scope) || entry.fund_id === draft.fund_id)
                .map((entry) => (
                  <option
                    key={entry.id}
                    value={entry.id}
                  >
                    {entry.name}
                  </option>
                ))}
            </NativeSelect>
          </label>
          {modeForFund === 's' && !item && !draft.contract_id && !draft.budget_id && (
            <p>{t('expenses.simpleHint')}</p>
          )}
          <div className={styles.buttons}>
            <Button
              type="button"
              variant="ghost"
              disabled={mutation.pending}
              onClick={onClose}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={
                mutation.pending ||
                !options ||
                ('equipmentId' in scope && !item && !draft.fund_id) ||
                (modeForFund === 's' && !item && !draft.contract_id && !draft.budget_id)
              }
            >
              {t('common.save')}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}

/** Confirm a destructive Expense action in its funding context. */
function ExpenseConfirmation({
  title,
  description,
  confirmLabel,
  returnFocus,
  onCancel,
  onConfirm,
  onDone,
}: {
  title: string;
  description: string;
  confirmLabel?: string;
  returnFocus: React.RefObject<HTMLElement | null>;
  onCancel: () => void;
  onConfirm: () => Promise<unknown>;
  onDone: () => void;
}) {
  const { t } = useTranslation();
  const mutation = useMutation();
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;
  async function confirm() {
    const result = await mutation.run(onConfirm);
    if (result) onDone();
  }
  return (
    <ConfirmDialog
      title={title}
      description={description}
      confirmLabel={confirmLabel}
      pending={mutation.pending}
      error={
        error && (
          <Alert tone="danger">
            {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
              t('expenses.saveError')}
          </Alert>
        )
      }
      onConfirm={() => void confirm()}
      onCancel={onCancel}
      returnFocus={returnFocus}
    />
  );
}
