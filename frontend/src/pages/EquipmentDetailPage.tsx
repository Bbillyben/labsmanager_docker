import { useMemo, useRef, useState } from 'react';
import { NavLink, Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import { FileDown, FileText, Pencil, Trash2 } from 'lucide-react';
import { ApiError, normalizeMutationError } from '../api/errors';
import {
  createEquipmentChild,
  deleteEquipment,
  deleteEquipmentChild,
  getEquipment,
  getEquipmentInfo,
  listEquipmentInfoTypes,
  updateEquipmentChild,
  type Equipment,
  type EquipmentInfoType,
} from '../api/equipment';
import { useMutation } from '../api/useMutation';
import type { ProjectGenericInfo } from '../api/projects';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { EntityActionMenu } from '../components/EntityActionMenu';
import { GenericNotes } from '../components/GenericNotes';
import { LoadingState } from '../components/LoadingState';
import { ObjectPreferenceActions } from '../components/ObjectPreferenceActions';
import { ReportExportDialog } from '../components/ReportExportDialog';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { PageHeader } from '../ui/PageHeader';
import { StatusBadge } from '../ui/StatusBadge';
import { EquipmentFormSheet } from './EquipmentFormSheet';
import { EquipmentRelationSection } from './EquipmentRelationSection';
import { EquipmentMaintenanceSection } from './EquipmentMaintenanceSection';
import { ExpenseSection } from './ExpenseSection';
import { GenericInfoSection } from './GenericInfoSection';
import { useEmployeeResource } from './useEmployeeResource';
import styles from './EmployeeDetailPage.module.css';
import overviewStyles from './ProjectOverview.module.css';

const sections = [
  { path: '', label: 'equipment.overview' },
  { path: 'maintenance', label: 'equipmentMaintenance.title' },
  { path: 'expenses', label: 'equipmentExpenses.title' },
  { path: 'notes', label: 'equipment.notes' },
] as const;

/** Keep child requests scoped to the selected detail section. */
export function EquipmentDetailPage() {
  const { t, language } = useTranslation();
  const { equipmentId = '' } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const resource = useEmployeeResource(equipmentId, getEquipment);
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [exportFormat, setExportFormat] = useState<'word' | 'pdf' | null>(null);
  const trigger = useRef<HTMLElement | null>(null);
  const mutation = useMutation();
  const error = mutation.error ? normalizeMutationError(mutation.error) : null;
  const base = `/equipment/${equipmentId}`;
  const tab = location.pathname.replace(/\/$/, '').split('/').at(-1);
  const section =
    tab === 'notes'
      ? 'notes'
      : tab === 'expenses'
        ? 'expenses'
        : tab === 'maintenance'
          ? 'maintenance'
          : '';

  async function remove(item: Equipment) {
    const result = await mutation.run(() => deleteEquipment(item.id));
    if (result) navigate('/equipment/');
  }
  if (tab !== equipmentId && tab !== 'notes' && tab !== 'expenses' && tab !== 'maintenance')
    return (
      <Navigate
        to={base}
        replace
      />
    );
  if (resource.loading) return <LoadingState message={t('equipment.loading')} />;
  if (resource.error || !resource.data) {
    const code = resource.error instanceof ApiError ? resource.error.status : 0;
    return (
      <Alert tone="danger">
        {code === 404
          ? t('equipment.notFound')
          : code === 403
            ? t('equipment.forbidden')
            : t('equipment.loadError')}{' '}
        <Button
          variant="ghost"
          onClick={resource.retry}
        >
          {t('common.retry')}
        </Button>
      </Alert>
    );
  }
  const item = resource.data;
  const date = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(
          new Date(`${value}T12:00:00`),
        )
      : '—';
  return (
    <>
      {location.state?.equipmentCreated && <Alert tone="success">{t('equipment.created')}</Alert>}
      <PageHeader
        title={item.name}
        meta={
          <div className="flex flex-wrap gap-2">
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
            <span>{item.internal_reference}</span>
          </div>
        }
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <ObjectPreferenceActions
              key={item.id}
              type="equipment"
              objectId={item.id}
            />
            <EntityActionMenu
              label={t('reports.entityActions', { name: item.name })}
              groups={[
                [
                  ...(item.capabilities.can_change
                    ? [
                        {
                          id: 'edit',
                          label: t('common.edit'),
                          icon: <Pencil aria-hidden="true" />,
                          onSelect: () => setEditing(true),
                        },
                      ]
                    : []),
                  ...(item.capabilities.can_delete
                    ? [
                        {
                          id: 'delete',
                          label: t('common.delete'),
                          icon: <Trash2 aria-hidden="true" />,
                          onSelect: () => setDeleting(true),
                        },
                      ]
                    : []),
                ],
                [
                  ...(item.capabilities.can_export_word
                    ? [
                        {
                          id: 'word',
                          label: t('reports.word'),
                          icon: <FileText aria-hidden="true" />,
                          onSelect: () => setExportFormat('word' as const),
                        },
                      ]
                    : []),
                  ...(item.capabilities.can_export_pdf
                    ? [
                        {
                          id: 'pdf',
                          label: t('reports.pdf'),
                          icon: <FileDown aria-hidden="true" />,
                          onSelect: () => setExportFormat('pdf' as const),
                        },
                      ]
                    : []),
                ],
              ]}
              adminUrl={item.admin_url}
              onTrigger={(element) => {
                trigger.current = element;
              }}
              finalFocus={() => (editing || deleting || exportFormat ? false : true)}
            />
          </div>
        }
      />
      <nav
        aria-label={t('equipment.navigation')}
        className={styles.resourceNav}
      >
        <div
          className={styles.resourceNavScroll}
          tabIndex={0}
        >
          {sections
            .filter(
              (entry) => entry.path !== 'maintenance' || item.capabilities.can_view_maintenance,
            )
            .map((entry) => (
              <NavLink
                key={entry.path}
                end
                className={({ isActive }) =>
                  `${styles.resourceLink} ${isActive ? styles.resourceLinkActive : ''}`
                }
                to={entry.path ? `${base}/${entry.path}` : base}
              >
                {t(entry.label)}
              </NavLink>
            ))}
        </div>
      </nav>
      <div className={styles.panel}>
        {section === '' && (
          <div
            className={overviewStyles.grid}
            aria-label={t('equipment.overview')}
          >
            <div className={overviewStyles.column}>
              <section className="min-w-0">
                <h2 className="mb-3 border-b border-border pb-2 text-base font-semibold">
                  {t('equipment.information')}
                </h2>
                <dl className={overviewStyles.details}>
                  <div>
                    <dt className="text-sm text-muted-foreground">{t('equipment.reference')}</dt>
                    <dd>{item.internal_reference}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">{t('equipment.category')}</dt>
                    <dd>
                      {item.category.path || item.category.name}
                      {!item.category.is_active ? ` (${t('common.inactive')})` : ''}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">{t('equipment.status')}</dt>
                    <dd>{t(`equipment.status.${item.status}`)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">
                      {t('equipment.acquisitionDate')}
                    </dt>
                    <dd>{date(item.acquisition_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">
                      {t('equipment.commissioningDate')}
                    </dt>
                    <dd>{date(item.commissioning_date)}</dd>
                  </div>
                  <div>
                    <dt className="text-sm text-muted-foreground">
                      {t('equipment.decommissioningDate')}
                    </dt>
                    <dd>{date(item.decommissioning_date)}</dd>
                  </div>
                </dl>
              </section>
              <div className={overviewStyles.stacked}>
                <section className="min-w-0">
                  <h2 className="mb-3 text-base font-semibold">{t('equipment.genericInfo')}</h2>
                  <EquipmentGenericInfo equipmentId={equipmentId} />
                </section>
              </div>
            </div>
            <div className={overviewStyles.column}>
              <EquipmentRelationSection
                equipmentId={equipmentId}
                kind="responsibilities"
              />
            </div>
            <div className={overviewStyles.column}>
              <EquipmentRelationSection
                equipmentId={equipmentId}
                kind="institutions"
              />
            </div>
          </div>
        )}
        {section === 'notes' && (
          <GenericNotes
            scope="equipment"
            objectId={equipmentId}
          />
        )}
        {section === 'expenses' && (
          <ExpenseSection
            scope={{ equipmentId: item.id }}
            title={t('equipmentExpenses.title')}
          />
        )}
        {section === 'maintenance' && <EquipmentMaintenanceSection equipmentId={equipmentId} />}
      </div>
      {editing && (
        <EquipmentFormSheet
          equipment={item}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            resource.updateData(() => saved);
            setEditing(false);
          }}
        />
      )}
      {deleting && (
        <ConfirmDialog
          title={t('equipment.deleteTitle')}
          description={t('equipment.deleteDescription', { name: item.name })}
          pending={mutation.pending}
          error={
            error && (
              <Alert tone="danger">
                {[...error.messages, ...Object.values(error.fields).flat()].join(' ') ||
                  t('equipment.deleteError')}
              </Alert>
            )
          }
          onCancel={() => setDeleting(false)}
          onConfirm={() => void remove(item)}
          returnFocus={trigger}
          destructive
        />
      )}
      {exportFormat && (
        <ReportExportDialog
          entity="equipment"
          id={item.id}
          format={exportFormat}
          title={t('reports.equipmentTitle', {
            format: t(exportFormat === 'word' ? 'reports.word' : 'reports.pdf'),
          })}
          timeframe={false}
          returnFocus={trigger}
          onClose={() => setExportFormat(null)}
        />
      )}
    </>
  );
}

const infoLoader = (id: string, signal: AbortSignal) => getEquipmentInfo(id, signal);

function EquipmentGenericInfo({ equipmentId }: { equipmentId: string }) {
  const { t } = useTranslation();
  const resource = useEmployeeResource(equipmentId, infoLoader);
  const api = useMemo(
    () => ({
      types: async (signal: AbortSignal): Promise<EquipmentInfoType[]> =>
        (await listEquipmentInfoTypes(signal)).items,
      create: (value: { type_id: number; value: string }) =>
        createEquipmentChild<ProjectGenericInfo>(equipmentId, 'generic-info', value),
      update: (id: number, value: string) =>
        updateEquipmentChild<ProjectGenericInfo>(equipmentId, 'generic-info', id, { value }),
      delete: (id: number) => deleteEquipmentChild(equipmentId, 'generic-info', id),
    }),
    [equipmentId],
  );
  return (
    <section aria-label={t('equipment.genericInfo')}>
      <GenericInfoSection
        api={api}
        data={resource.data}
        loading={resource.loading}
        error={resource.error}
        retry={resource.retry}
        refreshing={resource.refreshing}
        refreshError={resource.refreshError}
        refresh={resource.refresh}
        update={resource.updateData}
      />
    </section>
  );
}
