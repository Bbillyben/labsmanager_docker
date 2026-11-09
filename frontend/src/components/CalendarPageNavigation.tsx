import { useCallback, useContext, type ReactNode } from 'react';
import { CalendarDays, Copy, ExternalLink, Info, Link2, Play } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { getUIPages, type UIContribution } from '../api/uiContributions';
import { AuthContext } from '../auth/AuthContext';
import { useTranslation } from '../i18n/i18n';
import { useEmployeeResource } from '../pages/useEmployeeResource';
import { buttonVariants } from './ui/button';
import { Button } from '../ui/Button';
import styles from '../pages/EmployeeLeaves.module.css';

type NativeTab = 'employees' | 'projects' | 'maintenance';
type Props = {
  active: NativeTab | string;
  onSelectNative?: (tab: NativeTab) => void;
  actions?: ReactNode;
};
const icons = {
  calendar: CalendarDays,
  copy: Copy,
  'external-link': ExternalLink,
  link: Link2,
  info: Info,
  play: Play,
};

/** Render native and plugin calendar navigation entries. */
export function CalendarPageNavigation({ active, onSelectNative, actions }: Props) {
  const { language, t } = useTranslation();
  const auth = useContext(AuthContext);
  const canViewMaintenance =
    auth?.status === 'authenticated' && !!auth.user.capabilities.view_equipment_maintenance;
  const location = useLocation();
  const loader = useCallback((_key: string, signal: AbortSignal) => getUIPages(signal), []);
  const pages = useEmployeeResource('calendar-navigation-pages', loader);
  const pendingEntries = Array.isArray(location.state?.calendarNavigationEntries)
    ? (location.state.calendarNavigationEntries as UIContribution[])
    : [];
  const entries = (pages.data?.contributions ?? pendingEntries)
    .filter(
      (item): item is UIContribution & { local_id: string } =>
        item.type === 'page' && item.navigation?.location === 'calendars' && !!item.local_id,
    )
    .sort(
      (a, b) => (a.navigation?.order ?? 0) - (b.navigation?.order ?? 0) || a.id.localeCompare(b.id),
    );

  return (
    <div className={styles.calendarNavigation}>
      <div
        aria-label={t('calendars.title')}
        className={styles.segmented}
        role="group"
      >
        {(
          ['employees', 'projects', ...(canViewMaintenance ? ['maintenance'] : [])] as NativeTab[]
        ).map((tab) =>
          onSelectNative ? (
            <Button
              aria-pressed={active === tab}
              key={tab}
              onClick={() => onSelectNative(tab)}
              variant={active === tab ? 'default' : 'ghost'}
            >
              {t(
                tab === 'employees'
                  ? 'calendars.general'
                  : tab === 'projects'
                    ? 'calendars.projects'
                    : 'equipmentMaintenance.calendar',
              )}
            </Button>
          ) : (
            <Link
              aria-current={active === tab ? 'page' : undefined}
              className={buttonVariants({ variant: active === tab ? 'default' : 'ghost' })}
              key={tab}
              state={{ calendarNavigationEntries: entries }}
              to={`/calendars?tab=${tab}`}
            >
              {t(
                tab === 'employees'
                  ? 'calendars.general'
                  : tab === 'projects'
                    ? 'calendars.projects'
                    : 'equipmentMaintenance.calendar',
              )}
            </Link>
          ),
        )}
        {entries.map((item) => {
          const Icon = item.navigation?.icon
            ? icons[item.navigation.icon as keyof typeof icons]
            : undefined;
          const label = item.navigation?.labels[language] || item.label;
          return (
            <Link
              aria-current={active === item.id ? 'page' : undefined}
              className={buttonVariants({ variant: active === item.id ? 'default' : 'ghost' })}
              key={item.id}
              state={{ navigationLocation: 'calendars', calendarNavigationEntries: entries }}
              to={`/plugins/${encodeURIComponent(item.plugin_slug)}/${encodeURIComponent(item.local_id)}`}
            >
              {Icon && <Icon aria-hidden="true" />}
              {label}
            </Link>
          );
        })}
      </div>
      {actions && <div className={styles.calendarNavigationActions}>{actions}</div>}
    </div>
  );
}
