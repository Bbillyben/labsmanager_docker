import { useCallback, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import {
  createExpenseEquipmentAssignment,
  deleteExpenseEquipmentAssignment,
  getExpenseBusinessAssignments,
  updateExpenseEquipmentAssignment,
  type EquipmentExpenseNature,
} from '../api/expenses';
import { normalizeMutationError } from '../api/errors';
import { useMutation } from '../api/useMutation';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { NativeSelect } from '../components/ui/native-select';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { equipmentAssignmentSource } from '../config/equipmentAssignmentSource';
import { EntitySearch } from '../filters/EntitySearch';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { useEmployeeResource } from './useEmployeeResource';

type EditMode = 'link' | 'equipment' | 'nature' | null;

/** Expense-centered business assignments; Equipment is the only V1 domain section. */
export function ExpenseBusinessAssignments({
  expenseId,
  returnFocus,
  onClose,
  onChanged,
}: {
  expenseId: number;
  returnFocus: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  onChanged: () => void;
}) {
  const { t } = useTranslation();
  const loader = useCallback(
    (_id: string, signal: AbortSignal) => getExpenseBusinessAssignments(expenseId, signal),
    [expenseId],
  );
  const resource = useEmployeeResource(String(expenseId), loader);
  const mutation = useMutation();
  const [mode, setMode] = useState<EditMode>(null);
  const [equipmentId, setEquipmentId] = useState('');
  const [nature, setNature] = useState<EquipmentExpenseNature>('other');
  const [confirmUnlink, setConfirmUnlink] = useState(false);
  const confirmFocus = useRef<HTMLElement | null>(null);
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;
  const data = resource.data;
  const assignment = data?.equipment;

  function begin(nextMode: Exclude<EditMode, null>) {
    setEquipmentId(assignment ? String(assignment.equipment.id) : '');
    setNature(assignment?.nature ?? 'other');
    setMode(nextMode);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (mode !== 'nature' && !equipmentId) return;
    const result = await mutation.run(() => {
      if (mode === 'link')
        return createExpenseEquipmentAssignment(expenseId, Number(equipmentId), nature);
      if (mode === 'equipment')
        return updateExpenseEquipmentAssignment(expenseId, {
          equipment_id: Number(equipmentId),
          nature,
        });
      return updateExpenseEquipmentAssignment(expenseId, { nature });
    });
    if (result) {
      setMode(null);
      await resource.refresh();
      onChanged();
    }
  }

  async function unlink() {
    const result = await mutation.run(() => deleteExpenseEquipmentAssignment(expenseId));
    if (result) {
      setConfirmUnlink(false);
      await resource.refresh();
      onChanged();
    }
  }

  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open && !mutation.pending && !confirmUnlink) onClose();
      }}
    >
      <SheetContent finalFocus={returnFocus}>
        <SheetHeader>
          <SheetTitle>{t('expenseAssignments.title')}</SheetTitle>
          <SheetDescription>{t('expenseAssignments.description')}</SheetDescription>
        </SheetHeader>
        {resource.loading && <p role="status">{t('common.loading')}</p>}
        {Boolean(resource.error) && (
          <Alert tone="danger">
            {t('expenseAssignments.loadError')}{' '}
            <Button
              variant="ghost"
              onClick={resource.retry}
            >
              {t('common.retry')}
            </Button>
          </Alert>
        )}
        {Boolean(resource.refreshError) && (
          <Alert tone="warning">{t('expenseAssignments.loadError')}</Alert>
        )}
        {error && (
          <Alert tone="danger">
            {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
              t('expenseAssignments.saveError')}
          </Alert>
        )}
        {data && (
          <section
            className="mt-6 grid gap-4"
            aria-label={t('expenseAssignments.equipment')}
          >
            <h3 className="text-base font-semibold">{t('expenseAssignments.equipment')}</h3>
            {assignment ? (
              <div className="grid gap-1 text-sm">
                <strong>{t('expenseAssignments.linkedEquipment')}</strong>
                <Link
                  to={`/equipment/${assignment.equipment.id}`}
                  onClick={onClose}
                >
                  {assignment.equipment.name} · {assignment.equipment.internal_reference}
                </Link>
                <span>
                  {t('expenseAssignments.purpose')}: {t(`equipmentExpenses.${assignment.nature}`)}
                </span>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('expenseAssignments.empty')}</p>
            )}
            {!mode && (
              <div className="flex flex-wrap gap-2">
                {!assignment && data.capabilities.can_link && (
                  <Button onClick={() => begin('link')}>{t('expenseAssignments.link')}</Button>
                )}
                {assignment && data.capabilities.can_change && (
                  <>
                    <Button onClick={() => begin('nature')}>
                      {t('equipmentExpenses.changeNature')}
                    </Button>
                    <Button onClick={() => begin('equipment')}>
                      {t('expenseAssignments.changeEquipment')}
                    </Button>
                  </>
                )}
                {assignment && data.capabilities.can_unlink && (
                  <Button
                    variant="ghost"
                    onClick={(event) => {
                      confirmFocus.current = event.currentTarget;
                      setConfirmUnlink(true);
                    }}
                  >
                    {t('expenseAssignments.unlink')}
                  </Button>
                )}
              </div>
            )}
            {mode && (
              <form
                className="grid gap-4"
                onSubmit={(event) => void save(event)}
              >
                {mode !== 'nature' && (
                  <EntitySearch
                    id={`expense-equipment-${expenseId}`}
                    label={t('expenseAssignments.equipment')}
                    value={equipmentId}
                    source={equipmentAssignmentSource}
                    onChange={setEquipmentId}
                  />
                )}
                <label className="grid gap-1">
                  {t('expenseAssignments.purpose')}
                  <NativeSelect
                    value={nature}
                    onChange={(event) => setNature(event.target.value as EquipmentExpenseNature)}
                  >
                    {(['purchase', 'maintenance', 'repair', 'other'] as const).map((value) => (
                      <option
                        key={value}
                        value={value}
                      >
                        {t(`equipmentExpenses.${value}`)}
                      </option>
                    ))}
                  </NativeSelect>
                </label>
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    disabled={mutation.pending || (mode !== 'nature' && !equipmentId)}
                  >
                    {t('common.save')}
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => setMode(null)}
                  >
                    {t('common.cancel')}
                  </Button>
                </div>
              </form>
            )}
          </section>
        )}
        {confirmUnlink && (
          <ConfirmDialog
            title={t('expenseAssignments.unlinkTitle')}
            description={t('expenseAssignments.unlinkDescription')}
            confirmLabel={t('expenseAssignments.unlink')}
            pending={mutation.pending}
            error={error ? <Alert tone="danger">{error.messages.join(' ')}</Alert> : undefined}
            returnFocus={confirmFocus}
            onCancel={() => setConfirmUnlink(false)}
            onConfirm={() => void unlink()}
          />
        )}
      </SheetContent>
    </Sheet>
  );
}
