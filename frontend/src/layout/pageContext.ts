import type { TranslationKey } from '../i18n/i18n';

type PageContext = {
  label: TranslationKey;
  parent?: { label: TranslationKey; href: string };
  dynamic?: boolean;
};

type RouteContext = PageContext & { matches: (pathname: string) => boolean };

const route = (pattern: RegExp, context: PageContext): RouteContext => ({
  ...context,
  matches: (pathname) => pattern.test(pathname),
});

/** Shared route titles and parent links for the application bar. */
const pageContexts: readonly RouteContext[] = [
  route(/^\/$/, { label: 'page.home' }),
  route(/^\/search$/, { label: 'globalSearch.results', dynamic: true }),
  route(/^\/dashboard$/, { label: 'navigation.dashboard', dynamic: true }),
  route(/^\/employees$/, { label: 'page.employees' }),
  route(/^\/employees\/[^/]+(?:\/.*)?$/, {
    label: 'page.employees',
    parent: { label: 'page.employees', href: '/employees/' },
    dynamic: true,
  }),
  route(/^\/projects$/, { label: 'navigation.projects' }),
  route(/^\/projects\/[^/]+(?:\/.*)?$/, {
    label: 'navigation.projects',
    parent: { label: 'navigation.projects', href: '/projects/' },
    dynamic: true,
  }),
  route(/^\/equipment$/, { label: 'equipment.title' }),
  route(/^\/equipment\/new$/, {
    label: 'equipment.create',
    parent: { label: 'equipment.title', href: '/equipment/' },
  }),
  route(/^\/equipment\/[^/]+(?:\/.*)?$/, {
    label: 'equipment.title',
    parent: { label: 'equipment.title', href: '/equipment/' },
    dynamic: true,
  }),
  route(/^\/teams$/, { label: 'navigation.teams' }),
  route(/^\/teams\/[^/]+(?:\/.*)?$/, {
    label: 'navigation.teams',
    parent: { label: 'navigation.teams', href: '/teams/' },
    dynamic: true,
  }),
  route(/^\/organizations\/institutions$/, { label: 'organization.institutions' }),
  route(/^\/organizations\/institutions\/[^/]+(?:\/.*)?$/, {
    label: 'organization.institutions',
    parent: { label: 'organization.institutions', href: '/organizations/institutions' },
    dynamic: true,
  }),
  route(/^\/organizations\/funders$/, { label: 'organization.funders' }),
  route(/^\/organizations\/funders\/[^/]+(?:\/.*)?$/, {
    label: 'organization.funders',
    parent: { label: 'organization.funders', href: '/organizations/funders' },
    dynamic: true,
  }),
  route(/^\/calendars$/, { label: 'calendars.title' }),
  route(/^\/tools\/import$/, { label: 'navigation.import' }),
  route(/^\/tools\/organization-chart$/, { label: 'organizationChart.title' }),
  route(/^\/tools\/contracts$/, { label: 'navigation.contracts' }),
  route(/^\/tools\/data-consistency$/, { label: 'dataConsistency.title' }),
  route(/^\/tools\/fund-items$/, { label: 'financial.fundItems' }),
  route(/^\/tools\/budgets$/, { label: 'financial.budgets' }),
  route(/^\/tools\/expenses$/, { label: 'financial.expenses' }),
  route(/^\/settings$/, { label: 'userSettings.title' }),
  route(/^\/settings\/user$/, { label: 'userSettings.user' }),
  route(/^\/settings\/interface$/, { label: 'userSettings.interface' }),
  route(/^\/settings\/notifications$/, { label: 'userSettings.notifications' }),
  route(/^\/settings\/common$/, { label: 'userSettings.common' }),
  route(/^\/settings\/stale$/, { label: 'userSettings.stale' }),
  route(/^\/settings\/my-plugins$/, { label: 'pluginSettings.mine' }),
  route(/^\/settings\/my-plugins\/[^/]+$/, {
    label: 'pluginSettings.mine',
    parent: { label: 'pluginSettings.mine', href: '/settings/my-plugins' },
    dynamic: true,
  }),
  route(/^\/settings\/lists\/[^/]+$/, { label: 'mutableLists.group', dynamic: true }),
  route(/^\/settings\/admin\/general$/, { label: 'settingsAdmin.general' }),
  route(/^\/settings\/admin$/, { label: 'settingsAdmin.administration' }),
  route(/^\/settings\/admin\/users$/, { label: 'settingsAdmin.users' }),
  route(/^\/settings\/admin\/notifications$/, { label: 'settingsAdmin.notifications' }),
  route(/^\/settings\/admin\/plugins$/, { label: 'settingsAdmin.plugins' }),
  route(/^\/settings\/admin\/plugins\/[^/]+$/, {
    label: 'settingsAdmin.plugins',
    parent: { label: 'settingsAdmin.plugins', href: '/settings/admin/plugins' },
    dynamic: true,
  }),
  route(/^\/plugins\/[^/]+\/[^/]+$/, { label: 'pluginUI.pages', dynamic: true }),
];

export function getPageContext(pathname: string): PageContext | null {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  return pageContexts.find((context) => context.matches(normalized)) ?? null;
}
