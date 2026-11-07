import { useEffect, useState, type FormEvent } from 'react';
import {
  createEquipment,
  listEquipmentCategories,
  updateEquipment,
  type Equipment,
  type EquipmentCategory,
  type EquipmentStatus,
} from '../api/equipment';
import { normalizeMutationError } from '../api/errors';
import { useMutation } from '../api/useMutation';
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

const statuses: EquipmentStatus[] = ['in_service', 'out_of_service', 'in_maintenance', 'retired'];

/** Edit only Equipment's own fields; historical relations have separate forms. */
export function EquipmentFormSheet({
  equipment,
  onClose,
  onSaved,
}: {
  equipment: Equipment | null;
  onClose: () => void;
  onSaved: (equipment: Equipment) => void;
}) {
  const { t } = useTranslation();
  const [name, setName] = useState(equipment?.name ?? '');
  const [reference, setReference] = useState(equipment?.internal_reference ?? '');
  const [categoryId, setCategoryId] = useState(String(equipment?.category.id ?? ''));
  const [status, setStatus] = useState<EquipmentStatus>(equipment?.status ?? 'in_service');
  const [acquisitionDate, setAcquisitionDate] = useState(equipment?.acquisition_date ?? '');
  const [commissioningDate, setCommissioningDate] = useState(equipment?.commissioning_date ?? '');
  const [decommissioningDate, setDecommissioningDate] = useState(
    equipment?.decommissioning_date ?? '',
  );
  const [categories, setCategories] = useState<EquipmentCategory[]>([]);
  const [catalogueError, setCatalogueError] = useState(false);
  const mutation = useMutation();
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;

  useEffect(() => {
    const controller = new AbortController();
    listEquipmentCategories(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setCategories(data.items);
      },
      () => {
        if (!controller.signal.aborted) setCatalogueError(true);
      },
    );
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const data = {
      name: name.trim(),
      category_id: Number(categoryId),
      status,
      acquisition_date: acquisitionDate || null,
      commissioning_date: commissioningDate || null,
      decommissioning_date: decommissioningDate || null,
    };
    const result = await mutation.run(() =>
      equipment
        ? updateEquipment(equipment.id, data)
        : createEquipment({ ...data, internal_reference: reference.trim() }),
    );
    if (result) onSaved(result.data);
  }

  const categoriesForSelection = categories.filter(
    (item) => item.is_active || item.id === equipment?.category.id,
  );
  return (
    <Sheet
      open
      onOpenChange={(open) => {
        if (!open && !mutation.pending) onClose();
      }}
    >
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{t(equipment ? 'equipment.edit' : 'equipment.create')}</SheetTitle>
          <SheetDescription>{t('equipment.formDescription')}</SheetDescription>
        </SheetHeader>
        <form
          className="grid gap-4"
          onSubmit={(event) => void submit(event)}
        >
          {catalogueError && <Alert tone="danger">{t('equipment.catalogueError')}</Alert>}
          {error && (
            <Alert tone="danger">
              {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
                t('equipment.saveError')}
            </Alert>
          )}
          <label className="grid gap-1">
            {t('equipment.name')}
            <input
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              required
              maxLength={150}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            {t('equipment.reference')}
            <input
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              required
              maxLength={100}
              value={reference}
              readOnly={!!equipment}
              onChange={(event) => setReference(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            {t('equipment.category')}
            <select
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              required
              value={categoryId}
              onChange={(event) => setCategoryId(event.target.value)}
            >
              <option value="">{t('equipment.chooseCategory')}</option>
              {categoriesForSelection.map((item) => (
                <option
                  key={item.id}
                  value={item.id}
                >
                  {item.name}
                  {!item.is_active ? ` (${t('common.inactive')})` : ''}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1">
            {t('equipment.status')}
            <select
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={status}
              onChange={(event) => setStatus(event.target.value as EquipmentStatus)}
            >
              {statuses.map((item) => (
                <option
                  key={item}
                  value={item}
                >
                  {t(`equipment.status.${item}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1">
            {t('equipment.acquisitionDate')}
            <input
              type="date"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={acquisitionDate}
              onChange={(event) => setAcquisitionDate(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            {t('equipment.commissioningDate')}
            <input
              type="date"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={commissioningDate}
              onChange={(event) => setCommissioningDate(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            {t('equipment.decommissioningDate')}
            <input
              type="date"
              className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={decommissioningDate}
              onChange={(event) => setDecommissioningDate(event.target.value)}
            />
          </label>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
            >
              {t('common.cancel')}
            </Button>
            <Button
              type="submit"
              disabled={
                mutation.pending ||
                catalogueError ||
                !categoryId ||
                !name.trim() ||
                !reference.trim()
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
