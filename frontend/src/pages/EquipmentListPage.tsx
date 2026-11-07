import type { FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { ApiError } from '../api/errors';
import {
  getEquipmentCapabilities,
  listEquipment,
  listEquipmentCategories,
  type EquipmentCategory,
  type EquipmentStatus,
} from '../api/equipment';
import { FilterBar } from '../filters/FilterBar';
import { employeeFilterSources } from '../config/employeeFilterSources';
import { equipmentInstitutionSource } from '../config/equipmentInstitutionSource';
import type { SupportedFilter } from '../filters/types';
import { useTranslation } from '../i18n/i18n';
import { Alert } from '../ui/Alert';
import { Button } from '../ui/Button';
import { EmptyState } from '../ui/EmptyState';
import { PageHeader } from '../ui/PageHeader';
import { StatusBadge } from '../ui/StatusBadge';
import { useEmployeeResource } from './useEmployeeResource';
import { EquipmentFormSheet } from './EquipmentFormSheet';
import tableStyles from './EmployeeListPage.module.css';

const pageSize = 25;
const categoryLoader = (_id: string, signal: AbortSignal) => listEquipmentCategories(signal);
const capabilityLoader = (_id: string, signal: AbortSignal) => getEquipmentCapabilities(signal);
const equipmentLoader = (query: string, signal: AbortSignal) => listEquipment(query, signal);
const statusValues: EquipmentStatus[] = [
  'in_service',
  'out_of_service',
  'in_maintenance',
  'retired',
];

function CompactRelations({
  values,
  path,
  restricted,
}: {
  values: Array<{ id: number | null; name: string | null }>;
  path: string;
  restricted: string;
}) {
  if (!values.length) return <>—</>;
  const names = values.map((value) => (value.id ? value.name : restricted));
  const render = (value: (typeof values)[number], index: number) => (
    <span key={`${value.id ?? 'hidden'}:${index}`}>
      {index > 0 && ', '}
      {value.id ? <Link to={`${path}/${value.id}`}>{value.name}</Link> : restricted}
    </span>
  );
  if (values.length <= 2) return <span>{values.map(render)}</span>;
  return (
    <details title={names.join(', ')}>
      <summary className="cursor-pointer">
        {names.slice(0, 2).join(', ')} +{values.length - 2}
      </summary>
      <div className="min-w-0">{values.map(render)}</div>
    </details>
  );
}

/** Browse one server page of Equipment with URL-backed filters. */
export function EquipmentListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [query, setQuery] = useSearchParams();
  const categories = useEmployeeResource('equipment-categories', categoryLoader);
  const request = new URLSearchParams(query);
  request.set('limit', String(pageSize));
  const offset = Math.max(0, Number.parseInt(query.get('offset') ?? '0', 10) || 0);
  request.set('offset', String(offset));
  const resource = useEmployeeResource(request.toString(), equipmentLoader);

  const filters: SupportedFilter[] = [
    {
      id: 'category',
      label: t('equipment.category'),
      category: t('filters.categoryProject'),
      type: 'dynamic-choice',
      parameter: 'category',
      source: 'categories',
    },
    {
      id: 'status',
      label: t('equipment.status'),
      category: t('filters.categorySituation'),
      type: 'static-choice',
      parameter: 'status',
      options: statusValues.map((value) => ({ value, label: t(`equipment.status.${value}`) })),
    },
    {
      id: 'responsible',
      label: t('equipment.currentResponsible'),
      category: t('filters.categorySituation'),
      type: 'entity-search',
      parameter: 'responsible',
      source: 'employees',
      idFormat: 'positive-integer',
    },
    {
      id: 'institution',
      label: t('equipment.currentInstitution'),
      category: t('filters.categorySituation'),
      type: 'entity-search',
      parameter: 'institution',
      source: 'institutions',
      idFormat: 'positive-integer',
    },
  ];
  const updateQuery = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(query);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    next.delete('offset');
    setQuery(next);
  };
  const submitSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateQuery({ search: String(new FormData(event.currentTarget).get('search') ?? '').trim() });
  };
  const errorStatus = resource.error instanceof ApiError ? resource.error.status : 0;
  const hasFilters = !!(
    query.get('search') ||
    query.get('category') ||
    query.get('status') ||
    query.get('responsible') ||
    query.get('institution')
  );

  return (
    <>
      <PageHeader
        title={t('equipment.title')}
        actions={
          <div className="flex flex-wrap gap-2">
            {resource.data?.capabilities.can_add && (
              <Button onClick={() => navigate('/equipment/new')}>
                <Plus aria-hidden="true" />
                {t('equipment.create')}
              </Button>
            )}
          </div>
        }
      />
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <form
          role="search"
          onSubmit={submitSearch}
          className="flex gap-2"
        >
          <label className="grid gap-1 text-sm">
            {t('equipment.search')}
            <input
              key={query.get('search') ?? ''}
              name="search"
              className="h-9 rounded-md border border-input bg-background px-3"
              defaultValue={query.get('search') ?? ''}
            />
          </label>
          <Button type="submit">{t('common.search')}</Button>
        </form>
        <label className="grid gap-1 text-sm">
          {t('equipment.sort')}
          <select
            className="h-9 rounded-md border border-input bg-background px-3"
            value={query.get('ordering') ?? 'name'}
            onChange={(event) =>
              updateQuery({ ordering: event.target.value === 'name' ? null : event.target.value })
            }
          >
            <option value="name">{t('equipment.sortName')}</option>
            <option value="internal_reference">{t('equipment.sortReference')}</option>
            <option value="category__name">{t('equipment.sortCategory')}</option>
            <option value="status">{t('equipment.sortStatus')}</option>
          </select>
        </label>
        {hasFilters && (
          <Button
            variant="ghost"
            onClick={() => {
              setQuery(new URLSearchParams());
            }}
          >
            {t('list.searchReset')}
          </Button>
        )}
      </div>
      {categories.data && (
        <FilterBar
          catalogue={filters}
          sources={{
            employees: employeeFilterSources.allEmployees,
            institutions: equipmentInstitutionSource,
          }}
          choiceOptions={{
            categories: categories.data.items.map((item: EquipmentCategory) => ({
              value: String(item.id),
              label: item.name,
            })),
          }}
          query={query}
          onChange={(next) => {
            next.delete('offset');
            setQuery(next);
          }}
          resetParameters={['offset']}
        />
      )}
      {categories.error && <Alert tone="warning">{t('equipment.catalogueError')}</Alert>}
      {resource.loading && <p role="status">{t('equipment.loading')}</p>}
      {resource.error && (
        <Alert tone="danger">
          {errorStatus === 403 ? t('equipment.forbidden') : t('equipment.loadError')}{' '}
          <Button
            variant="ghost"
            onClick={resource.retry}
          >
            {t('common.retry')}
          </Button>
        </Alert>
      )}
      {resource.data && (
        <>
          {!resource.data.results.length && (
            <EmptyState title={hasFilters ? t('equipment.noResults') : t('equipment.empty')} />
          )}
          {!!resource.data.results.length && (
            <div
              className={tableStyles.scroll}
              role="region"
              aria-label={t('equipment.title')}
              tabIndex={0}
            >
              <table className={tableStyles.table}>
                <thead>
                  <tr>
                    <th scope="col">{t('equipment.name')}</th>
                    <th scope="col">{t('equipment.reference')}</th>
                    <th scope="col">{t('equipment.category')}</th>
                    <th scope="col">{t('equipment.status')}</th>
                    <th scope="col">{t('equipment.currentResponsible')}</th>
                    <th scope="col">{t('equipment.currentInstitution')}</th>
                  </tr>
                </thead>
                <tbody>
                  {resource.data.results.map((item) => (
                    <tr key={item.id}>
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
                      <td>
                        <CompactRelations
                          values={item.current_responsibles}
                          path="/employees"
                          restricted={t('equipment.restrictedRelation')}
                        />
                      </td>
                      <td>
                        <CompactRelations
                          values={item.current_institutions}
                          path="/organizations/institutions"
                          restricted={t('equipment.restrictedRelation')}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className={tableStyles.pagination}>
            <span>{t('equipment.count', { count: resource.data.count })}</span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                disabled={!resource.data.previous}
                onClick={() => {
                  const next = new URLSearchParams(query);
                  next.set('offset', String(Math.max(0, offset - pageSize)));
                  setQuery(next);
                }}
              >
                {t('common.previous')}
              </Button>
              <Button
                variant="secondary"
                disabled={!resource.data.next}
                onClick={() => {
                  const next = new URLSearchParams(query);
                  next.set('offset', String(offset + pageSize));
                  setQuery(next);
                }}
              >
                {t('common.next')}
              </Button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

/** A dedicated URL keeps creation reloadable while reusing the same Sheet. */
export function EquipmentCreatePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const rights = useEmployeeResource('equipment-create', capabilityLoader);
  if (rights.loading) return <p role="status">{t('equipment.loading')}</p>;
  if (!rights.data?.can_add) return <Alert tone="danger">{t('equipment.forbidden')}</Alert>;
  return (
    <EquipmentFormSheet
      equipment={null}
      onClose={() => navigate('/equipment/')}
      onSaved={(item) => navigate(`/equipment/${item.id}`, { state: { equipmentCreated: true } })}
    />
  );
}
