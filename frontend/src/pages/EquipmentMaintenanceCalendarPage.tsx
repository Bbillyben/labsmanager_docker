import { useCallback } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { equipmentMaintenanceCalendar } from '../api/equipmentMaintenance';
import { SharedCalendar } from '../calendar/SharedCalendar';
import { localToday } from '../calendar/resourceVisibility';
import { equipmentAssignmentSource } from '../config/equipmentAssignmentSource';
import { EntitySearch } from '../filters/EntitySearch';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { PageHeader } from '../ui/PageHeader';
import { PrintButton } from '../print/PrintButton';
import type { CalendarPrintState } from '../print/CalendarPrintView';
import {
  projectCalendarRange,
  projectCalendarScopeOrder,
  projectCalendarScopes,
  projectCalendarViewDefinition,
  shiftProjectCalendarAnchor,
} from './projectCalendarScopes';
import { useEmployeeResource } from './useEmployeeResource';

/** Reuse the native calendar presentation for the dedicated Equipment scope. */
export function EquipmentMaintenanceCalendarPage({
  embedded = false,
  onOpenMaintenance,
}: {
  embedded?: boolean;
  onOpenMaintenance?: (id: number) => void;
} = {}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { equipmentId } = useParams();
  const [query, setQuery] = useSearchParams();
  const date = query.get('date') ?? localToday();
  const anchor = /^\d{4}-\d{2}-\d{2}$/.test(date) ? new Date(`${date}T12:00:00`) : new Date();
  const scope = projectCalendarScopeOrder.find((value) => value === query.get('view')) ?? 'month';
  const range = projectCalendarRange(scope, anchor);
  const requestQuery = new URLSearchParams(range);
  const typeParameter = embedded ? 'maintenanceType' : 'type';
  const statusParameter = embedded ? 'maintenanceStatus' : 'status';
  if (!equipmentId && query.get('equipment'))
    requestQuery.set('equipment', query.get('equipment')!);
  if (query.get(typeParameter)) requestQuery.set('maintenance_type', query.get(typeParameter)!);
  if (query.get(statusParameter)) requestQuery.set('status', query.get(statusParameter)!);
  if (embedded && query.get('maintenanceOverdue') === '1') requestQuery.set('overdue', '1');
  const loader = useCallback(
    (key: string, signal: AbortSignal) =>
      equipmentMaintenanceCalendar(equipmentId ?? null, key, signal),
    [equipmentId],
  );
  const resource = useEmployeeResource(requestQuery.toString(), loader);
  function change(key: string, value: string) {
    const next = new URLSearchParams(query);
    if (value) next.set(key, value);
    else next.delete(key);
    setQuery(next);
  }
  function move(direction: -1 | 1 | 0) {
    const next =
      direction === 0 ? new Date() : shiftProjectCalendarAnchor(anchor, scope, direction);
    const formatted = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-${String(next.getDate()).padStart(2, '0')}`;
    change('date', formatted);
  }
  return (
    <section className="grid gap-4">
      {!embedded && <PageHeader title={t('equipmentMaintenance.calendar')} />}
      {!embedded && equipmentId && (
        <Link to={`/equipment/${equipmentId}/maintenance`}>{t('equipmentMaintenance.back')}</Link>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          variant="ghost"
          onClick={() => move(-1)}
        >
          {t('common.previous')}
        </Button>
        <Button
          variant="ghost"
          onClick={() => move(0)}
        >
          {t('equipmentMaintenance.today')}
        </Button>
        <Button
          variant="ghost"
          onClick={() => move(1)}
        >
          {t('common.next')}
        </Button>
        <select
          aria-label={t('equipmentMaintenance.period')}
          value={scope}
          onChange={(event) => change('view', event.target.value)}
        >
          {projectCalendarScopeOrder.map((value) => (
            <option
              key={value}
              value={value}
            >
              {t(projectCalendarScopes[value].label)}
            </option>
          ))}
        </select>
        {!equipmentId && (
          <EntitySearch
            id="maintenance-calendar-equipment"
            label={t('equipment.title')}
            value={query.get('equipment') ?? ''}
            source={equipmentAssignmentSource}
            onChange={(value) => change('equipment', value)}
          />
        )}
        <select
          aria-label={t('equipmentMaintenance.type')}
          value={query.get(typeParameter) ?? ''}
          onChange={(event) => change(typeParameter, event.target.value)}
        >
          <option value="">{t('equipmentMaintenance.all')}</option>
          {(['preventive', 'corrective', 'inspection', 'calibration', 'other'] as const).map(
            (value) => (
              <option
                key={value}
                value={value}
              >
                {t(`equipmentMaintenance.type.${value}`)}
              </option>
            ),
          )}
        </select>
        <select
          aria-label={t('equipmentMaintenance.status')}
          value={query.get(statusParameter) ?? ''}
          onChange={(event) => change(statusParameter, event.target.value)}
        >
          <option value="">{t('equipmentMaintenance.all')}</option>
          {(['planned', 'in_progress', 'completed', 'cancelled'] as const).map((value) => (
            <option
              key={value}
              value={value}
            >
              {t(`equipmentMaintenance.status.${value}`)}
            </option>
          ))}
        </select>
        {resource.data && (
          <PrintButton
            createRequest={() => ({
              renderer: 'calendar',
              title: t('equipmentMaintenance.calendar'),
              state: {
                scope,
                viewType: projectCalendarViewDefinition(scope, 'calendar').key,
                mode: 'calendar',
                range,
                events: resource.data?.events ?? [],
              } satisfies CalendarPrintState,
            })}
          />
        )}
      </div>
      {resource.loading && <p role="status">{t('common.loading')}</p>}
      {Boolean(resource.error) && (
        <Alert tone="danger">
          {t('equipmentMaintenance.loadError')}{' '}
          <Button onClick={resource.retry}>{t('common.retry')}</Button>
        </Alert>
      )}
      {resource.data && (
        <SharedCalendar
          anchor={anchor}
          scope={scope}
          viewMode="calendar"
          events={resource.data.events}
          onOpen={(event) => {
            const id = Number(event.metadata.equipment_id);
            const maintenanceId = Number(event.metadata.maintenance_id);
            if (id > 0 && maintenanceId > 0) {
              if (onOpenMaintenance) onOpenMaintenance(maintenanceId);
              else navigate(`/equipment/${id}/maintenance?maintenance=${maintenanceId}`);
            }
          }}
        />
      )}
    </section>
  );
}
