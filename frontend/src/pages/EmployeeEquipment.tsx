import { Fragment, useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { listEquipment, type Equipment } from '../api/equipment';
import { listEquipmentMaintenances, type EquipmentMaintenance } from '../api/equipmentMaintenance';
import { useAuth } from '../auth/AuthContext';
import { SelectableTableRow } from '../components/SelectableTableRow';
import { useTranslation, type Language } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { StatusBadge } from '../ui/StatusBadge';
import { useEmployeeDetail } from './employeeDetailContext';
import { useEmployeeResource } from './useEmployeeResource';
import tableStyles from './EmployeeListPage.module.css';
import styles from './EmployeeEquipment.module.css';

const pageSize = 25;
const dateLabel = (value: string | null, language: Language) =>
  value
    ? new Intl.DateTimeFormat(language, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      }).format(new Date(`${value}T12:00:00`))
    : '—';

/** Read the Equipment catalogue through its existing responsible filter. */
export function EmployeeEquipment() {
  const { employeeId } = useEmployeeDetail();
  const auth = useAuth();
  const { t, language } = useTranslation();
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const allowed = auth.status === 'authenticated' && auth.user.capabilities.view_equipment_list;
  const canViewMaintenance =
    auth.status === 'authenticated' && auth.user.capabilities.view_equipment_maintenance === true;
  const query = new URLSearchParams({
    responsible: employeeId,
    limit: String(pageSize),
    offset: String(offset),
  });
  const resource = useEmployeeResource(query.toString(), listEquipment, allowed);

  if (!allowed) return <Alert tone="danger">{t('equipment.forbidden')}</Alert>;
  if (resource.loading) return <p role="status">{t('equipment.loading')}</p>;
  if (resource.error || !resource.data)
    return (
      <Alert tone="danger">
        {t('equipment.loadError')} <Button onClick={resource.retry}>{t('common.retry')}</Button>
      </Alert>
    );
  if (!resource.data.results.length && offset === 0)
    return <EmptyState title={t('employee.equipmentEmpty')} />;

  return (
    <section aria-label={t('employee.navEquipment')}>
      <h2 className={styles.title}>{t('employee.navEquipment')}</h2>
      <div
        className={tableStyles.scroll}
        role="region"
        aria-label={t('employee.navEquipment')}
        tabIndex={0}
      >
        <table className={tableStyles.table}>
          <thead>
            <tr>
              <th scope="col">{t('equipment.name')}</th>
              <th scope="col">{t('equipment.reference')}</th>
              <th scope="col">{t('equipment.category')}</th>
              <th scope="col">{t('equipment.status')}</th>
              <th scope="col">{t('equipment.startDate')}</th>
              <th scope="col">{t('equipment.inventories')}</th>
            </tr>
          </thead>
          <tbody>
            {resource.data.results.map((item: Equipment) => (
              <Fragment key={item.id}>
                <SelectableTableRow
                  rowId={item.id}
                  selectedId={selectedId}
                  onSelect={canViewMaintenance ? setSelectedId : () => undefined}
                  className={canViewMaintenance ? undefined : styles.staticRow}
                  tabIndex={canViewMaintenance ? 0 : -1}
                  aria-expanded={canViewMaintenance ? selectedId === item.id : undefined}
                >
                  <th scope="row">
                    <Link to={`/equipment/${item.id}`}>{item.name}</Link>
                  </th>
                  <td>{item.internal_reference}</td>
                  <td>{item.category.name}</td>
                  <td>
                    <StatusBadge
                      tone={
                        item.status === 'in_service'
                          ? 'success'
                          : item.status === 'retired'
                            ? 'neutral'
                            : 'warning'
                      }
                    >
                      {t(`equipment.status.${item.status}`)}
                    </StatusBadge>
                  </td>
                  <td>{dateLabel(item.responsibility_start_date, language)}</td>
                  <td>
                    {item.current_inventories.length
                      ? item.current_inventories.map((inventory, index) => (
                          <span
                            key={`${inventory.institution}:${inventory.inventory_number}:${index}`}
                          >
                            {index > 0 && ', '}
                            {inventory.institution}
                            <i>
                              {inventory.inventory_number && ` · ${inventory.inventory_number}`}
                            </i>
                          </span>
                        ))
                      : '—'}
                  </td>
                </SelectableTableRow>
                {canViewMaintenance && selectedId === item.id && (
                  <tr className={styles.detailRow}>
                    <td colSpan={6}>
                      <MaintenanceHistory equipmentId={String(item.id)} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <div className={tableStyles.pagination}>
        <span>{t('equipment.count', { count: resource.data.count })}</span>
        <Button
          variant="secondary"
          disabled={!resource.data.previous}
          onClick={() => {
            setSelectedId(null);
            setOffset(Math.max(0, offset - pageSize));
          }}
        >
          {t('common.previous')}
        </Button>
        <Button
          variant="secondary"
          disabled={!resource.data.next}
          onClick={() => {
            setSelectedId(null);
            setOffset(offset + pageSize);
          }}
        >
          {t('common.next')}
        </Button>
      </div>
    </section>
  );
}

/** Mount only for the selected Equipment, so its full maintenance history loads on demand. */
function MaintenanceHistory({ equipmentId }: { equipmentId: string }) {
  const { t, language } = useTranslation();
  const [offset, setOffset] = useState(0);
  const loader = useCallback(
    (query: string, signal: AbortSignal) => listEquipmentMaintenances(equipmentId, query, signal),
    [equipmentId],
  );
  const query = new URLSearchParams({ limit: String(pageSize), offset: String(offset) });
  const resource = useEmployeeResource(query.toString(), loader);
  if (resource.loading) return <p role="status">{t('common.loading')}</p>;
  if (resource.error || !resource.data)
    return (
      <Alert tone="danger">
        {t('equipmentMaintenance.loadError')}{' '}
        <Button onClick={resource.retry}>{t('common.retry')}</Button>
      </Alert>
    );
  return (
    <div className={styles.maintenance}>
      <h3>{t('equipmentMaintenance.title')}</h3>
      {!resource.data.results.length && <p>{t('equipmentMaintenance.empty')}</p>}
      {resource.data.results.map((item: EquipmentMaintenance) => (
        <div
          className={styles.maintenanceItem}
          key={item.id}
        >
          <strong>{item.title}</strong>
          <span>{t(`equipmentMaintenance.type.${item.maintenance_type}`)}</span>
          <span>
            {t('equipmentMaintenance.scheduledDate')}: {dateLabel(item.scheduled_date, language)}
          </span>
          <StatusBadge
            tone={
              item.status === 'completed'
                ? 'success'
                : item.status === 'cancelled'
                  ? 'neutral'
                  : 'warning'
            }
          >
            {t(`equipmentMaintenance.status.${item.status}`)}
          </StatusBadge>
          {item.performed_date && (
            <span>
              {t('equipmentMaintenance.performedDate')}: {dateLabel(item.performed_date, language)}
            </span>
          )}
          {item.description && <p>{item.description}</p>}
          {item.report && (
            <p>
              {t('equipmentMaintenance.report')}: {item.report}
            </p>
          )}
        </div>
      ))}
      {(resource.data.previous || resource.data.next) && (
        <div className={tableStyles.pagination}>
          <Button
            variant="secondary"
            disabled={!resource.data.previous}
            onClick={() => setOffset(Math.max(0, offset - pageSize))}
          >
            {t('common.previous')}
          </Button>
          <Button
            variant="secondary"
            disabled={!resource.data.next}
            onClick={() => setOffset(offset + pageSize)}
          >
            {t('common.next')}
          </Button>
        </div>
      )}
    </div>
  );
}
