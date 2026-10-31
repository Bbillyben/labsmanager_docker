import {
  projectCalendarViewDefinition,
  type ProjectCalendarScope,
} from '../pages/projectCalendarScopes';

/** Display modes offered to an independently built calendar plugin. */
export type PluginCalendarMode = 'calendar' | 'list' | 'resources';
/** Minimal event shape accepted by the shared plugin calendar view. */
export type PluginCalendarEvent = {
  id: string;
  title: string;
  start: string;
  end: string;
  allDay?: boolean;
  color?: string;
  calendarName?: string;
  typeName?: string;
  employeeNames?: string[];
  resourceIds?: string[];
};
export type PluginCalendarResource = { id: string; title: string };
/** Exclusive end date and inclusive start date requested by the host view. */
export type PluginCalendarRange = { start: string; end: string };

/** Construct a stable identity for a plugin calendar view. */
export function pluginCalendarViewKey(scope: ProjectCalendarScope, mode: PluginCalendarMode) {
  return mode === 'list' ? `list_${scope}` : projectCalendarViewDefinition(scope, mode).key;
}

/** Include event-referenced resources and one row for unassigned events. */
export function pluginCalendarResources(
  events: PluginCalendarEvent[],
  resources: PluginCalendarResource[],
  unassigned: string,
) {
  const byId = new Map(resources.map((resource) => [resource.id, resource]));
  for (const event of events)
    for (const id of event.resourceIds ?? []) {
      if (!byId.has(id))
        byId.set(id, {
          id,
          title: event.employeeNames?.[(event.resourceIds ?? []).indexOf(id)] ?? id,
        });
    }
  return [...byId.values(), { id: '__calendar_unassigned__', title: unassigned }];
}
