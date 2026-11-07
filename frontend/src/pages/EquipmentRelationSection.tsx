import { useCallback, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { normalizeMutationError } from '../api/errors';
import {
  createEquipmentChild,
  deleteEquipmentChild,
  getEquipmentInventories,
  getEquipmentResponsibilities,
  updateEquipmentChild,
  type EquipmentInventory,
  type EquipmentResponsibility,
  type InventoryStatus,
} from '../api/equipment';
import { useMutation } from '../api/useMutation';
import type { ProjectCollection } from '../api/projects';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { CurrentPreviousList } from '../components/CurrentPreviousList';
import { ItemActionMenu } from '../components/ItemActionMenu';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '../components/ui/sheet';
import { employeeFilterSources } from '../config/employeeFilterSources';
import { equipmentInstitutionSource } from '../config/equipmentInstitutionSource';
import { EntitySearch } from '../filters/EntitySearch';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { StatusBadge } from '../ui/StatusBadge';
import { useEmployeeResource } from './useEmployeeResource';
import styles from './EmployeeDetailPage.module.css';

type Relation = EquipmentResponsibility | EquipmentInventory;
type Kind = 'responsibilities' | 'institutions';

/** Render active and historical lines without collapsing overlapping periods. */
export function EquipmentRelationSection({
  equipmentId,
  kind,
}: {
  equipmentId: string;
  kind: Kind;
}) {
  const { t, language } = useTranslation();
  const load = useCallback(
    async (_id: string, signal: AbortSignal): Promise<ProjectCollection<Relation>> =>
      kind === 'responsibilities'
        ? getEquipmentResponsibilities(equipmentId, signal)
        : getEquipmentInventories(equipmentId, signal),
    [equipmentId, kind],
  );
  const resource = useEmployeeResource(`${equipmentId}:${kind}`, load);
  const [editing, setEditing] = useState<Relation | 'new' | null>(null);
  const [deleting, setDeleting] = useState<Relation | null>(null);
  const deletion = useMutation();
  const trigger = useRef<HTMLElement | null>(null);
  const error = deletion.error ? normalizeMutationError(deletion.error) : null;
  const isInventory = kind === 'institutions';
  const title = t(isInventory ? 'equipment.inventories' : 'equipment.responsibilities');
  const date = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(
          new Date(`${value}T12:00:00`),
        )
      : '—';
  const entries = resource.data?.items ?? [];
  const current = entries.filter((item) => item.is_active);
  const previous = entries.filter((item) => !item.is_active);

  async function remove(item: Relation) {
    const result = await deletion.run(() => deleteEquipmentChild(equipmentId, kind, item.id));
    if (result) {
      setDeleting(null);
      void resource.refresh();
    }
  }

  function renderRelation(item: Relation) {
    const Row = isInventory ? 'li' : 'div';
    const inventory = isInventory ? (item as EquipmentInventory) : null;
    const responsibility = !isInventory ? (item as EquipmentResponsibility) : null;
    const target = inventory?.institution ?? responsibility?.employee;
    const name =
      inventory?.institution.short_name ??
      responsibility?.employee.name ??
      t('equipment.restrictedRelation');
    const link =
      target?.can_view && target.id
        ? inventory
          ? `/organizations/institutions/${target.id}`
          : `/employees/${target.id}`
        : null;
    return (
      <Row
        key={item.id}
        className={`flex min-w-0 items-start justify-between gap-2 py-2 text-sm ${isInventory ? '' : 'border-b border-border'}`}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            {link ? (
              <Link
                className="font-medium underline"
                to={link}
              >
                {name}
              </Link>
            ) : (
              <span className="font-medium">{name}</span>
            )}
            {inventory ? (
              <StatusBadge
                tone={inventory.status === 'registered' && item.is_active ? 'success' : 'neutral'}
              >
                {t(`equipment.inventory.${inventory.status}`)}
              </StatusBadge>
            ) : (
              <StatusBadge tone={item.is_active ? 'success' : 'neutral'}>
                {t(item.is_active ? 'equipment.current' : 'equipment.historical')}
              </StatusBadge>
            )}
          </div>
          <div className="mt-1 text-xs text-muted-foreground">
            {date(item.start_date)} – {date(item.end_date)}
            {inventory?.inventory_number && (
              <span>
                {' '}
                · {t('equipment.inventoryNumber')}: {inventory.inventory_number}
              </span>
            )}
          </div>
        </div>
        <ItemActionMenu
          label={t('equipment.relationActions')}
          canChange={resource.data?.capabilities.can_change ?? false}
          canDelete={resource.data?.capabilities.can_delete ?? false}
          onOpen={() => {}}
          onTrigger={(element) => {
            trigger.current = element;
          }}
          onEdit={() => setEditing(item)}
          onDelete={() => setDeleting(item)}
        />
      </Row>
    );
  }
  return (
    <section
      aria-label={title}
      className="grid gap-4"
    >
      <div className={styles.relationshipHeading}>
        <h2 className="text-lg font-semibold">{title}</h2>
        {resource.data?.capabilities.can_add && (
          <Button
            size="xs"
            variant="ghost"
            onClick={() => setEditing('new')}
          >
            <Plus aria-hidden="true" />
            {t('equipment.addRelation')}
          </Button>
        )}
      </div>
      {resource.loading && <p role="status">{t('equipment.loading')}</p>}
      {!!resource.error && (
        <Alert tone="danger">
          {t('equipment.loadError')}{' '}
          <Button
            variant="ghost"
            onClick={resource.retry}
          >
            {t('common.retry')}
          </Button>
        </Alert>
      )}
      {resource.data && !entries.length && <p>{t('equipment.noRelations')}</p>}
      {resource.data &&
        !!entries.length &&
        (isInventory ? (
          <ul className="divide-y divide-border">{entries.map(renderRelation)}</ul>
        ) : (
          <CurrentPreviousList
            current={current}
            previous={previous}
            empty={t('equipment.noneCurrently')}
            listClassName="grid gap-2"
            emptyClassName="text-sm text-muted-foreground"
            previousClassName="w-fit px-0 text-muted-foreground"
            render={renderRelation}
          />
        ))}
      {editing && (
        <RelationSheet
          equipmentId={equipmentId}
          kind={kind}
          item={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void resource.refresh();
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={t('equipment.deleteRelationTitle')}
          description={t('equipment.deleteRelationDescription')}
          pending={deletion.pending}
          error={
            error && (
              <Alert tone="danger">
                {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
                  t('equipment.deleteError')}
              </Alert>
            )
          }
          onConfirm={() => void remove(deleting)}
          onCancel={() => setDeleting(null)}
          returnFocus={trigger}
          destructive
        />
      )}
    </section>
  );
}

/** Create a new period or update only the dates and inventory metadata of one line. */
function RelationSheet({
  equipmentId,
  kind,
  item,
  onClose,
  onSaved,
}: {
  equipmentId: string;
  kind: Kind;
  item: Relation | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useTranslation();
  const isInventory = kind === 'institutions';
  const [targetId, setTargetId] = useState('');
  const [startDate, setStartDate] = useState(item?.start_date ?? '');
  const [endDate, setEndDate] = useState(item?.end_date ?? '');
  const inventory = isInventory && item ? (item as EquipmentInventory) : null;
  const [inventoryNumber, setInventoryNumber] = useState(inventory?.inventory_number ?? '');
  const [status, setStatus] = useState<InventoryStatus>(inventory?.status ?? 'registered');
  const mutation = useMutation();
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;
  async function submit(event: FormEvent) {
    event.preventDefault();
    const data = {
      start_date: startDate || null,
      end_date: endDate || null,
      ...(isInventory ? { inventory_number: inventoryNumber, status } : {}),
      ...(!item
        ? isInventory
          ? { institution_id: Number(targetId) }
          : { employee_id: Number(targetId) }
        : {}),
    };
    const result = await mutation.run(() =>
      item
        ? updateEquipmentChild<Relation>(equipmentId, kind, item.id, data)
        : createEquipmentChild<Relation>(equipmentId, kind, data),
    );
    if (result) onSaved();
  }
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open && !mutation.pending) onClose();
      }}
    >
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t(item ? 'equipment.editRelation' : 'equipment.addRelation')}</SheetTitle>
          <SheetDescription>{t('equipment.relationDescription')}</SheetDescription>
        </SheetHeader>
        <form
          className="grid gap-4"
          onSubmit={(event) => void submit(event)}
        >
          {error && (
            <Alert tone="danger">
              {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
                t('equipment.saveError')}
            </Alert>
          )}
          {!item ? (
            <EntitySearch
              id={`equipment-${kind}-target`}
              label={t(isInventory ? 'equipment.institution' : 'equipment.employee')}
              source={isInventory ? equipmentInstitutionSource : employeeFilterSources.allEmployees}
              value={targetId}
              onChange={setTargetId}
            />
          ) : (
            <p>
              {t(isInventory ? 'equipment.institution' : 'equipment.employee')}:{' '}
              {isInventory
                ? (inventory?.institution.short_name ?? t('equipment.restrictedRelation'))
                : ((item as EquipmentResponsibility).employee.name ??
                  t('equipment.restrictedRelation'))}
            </p>
          )}
          <label className="grid gap-1">
            {t('equipment.startDate')}
            <input
              type="date"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            {t('equipment.endDate')}
            <input
              type="date"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </label>
          {isInventory && (
            <>
              <label className="grid gap-1">
                {t('equipment.inventoryNumber')}
                <input
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  maxLength={100}
                  value={inventoryNumber}
                  onChange={(event) => setInventoryNumber(event.target.value)}
                />
              </label>
              <label className="grid gap-1">
                {t('equipment.status')}
                <select
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={status}
                  onChange={(event) => setStatus(event.target.value as InventoryStatus)}
                >
                  <option value="registered">{t('equipment.inventory.registered')}</option>
                  <option value="closed">{t('equipment.inventory.closed')}</option>
                </select>
              </label>
            </>
          )}
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              onClick={onClose}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={mutation.pending || (!item && !targetId)}
            >
              {t('common.save')}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
