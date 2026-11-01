import { describe, expect, it } from 'vitest';
import {
  projectCalendarRange,
  projectCalendarScopes,
  projectCalendarViewDefinition,
  shiftProjectCalendarAnchor,
  type ProjectCalendarScope,
} from './projectCalendarScopes';

describe('Project Calendar temporal scopes', () => {
  const anchor = new Date(2028, 0, 31);
  it.each([
    [
      'fifteenDays',
      { from: '2028-01-31', to: '2028-02-14' },
      { from: '2028-02-07', to: '2028-02-21' },
      { from: '2028-01-24', to: '2028-02-07' },
    ],
    [
      'month',
      { from: '2028-01-01', to: '2028-01-31' },
      { from: '2028-02-01', to: '2028-02-29' },
      { from: '2027-12-01', to: '2027-12-31' },
    ],
    [
      'twoMonths',
      { from: '2028-01-01', to: '2028-02-29' },
      { from: '2028-02-01', to: '2028-03-31' },
      { from: '2027-12-01', to: '2028-01-31' },
    ],
    [
      'year',
      { from: '2028-01-01', to: '2028-12-31' },
      { from: '2029-01-01', to: '2029-12-31' },
      { from: '2027-01-01', to: '2027-12-31' },
    ],
  ] as Array<
    [
      ProjectCalendarScope,
      { from: string; to: string },
      { from: string; to: string },
      { from: string; to: string },
    ]
  >)('%s has bounded dates and exact navigation', (scope, current, next, previous) => {
    expect(projectCalendarRange(scope, anchor)).toEqual(current);
    expect(projectCalendarRange(scope, shiftProjectCalendarAnchor(anchor, scope, 1))).toEqual(next);
    expect(projectCalendarRange(scope, shiftProjectCalendarAnchor(anchor, scope, -1))).toEqual(
      previous,
    );
  });

  it.each([
    ['fifteenDays', 'calendar', 'dayGridFifteenDays', 'dayGrid'],
    ['month', 'calendar', 'dayGridMonthCustom', 'dayGrid'],
    ['twoMonths', 'calendar', 'dayGridTwoMonths', 'timeline'],
    ['year', 'calendar', 'dayGridYearCustom', 'timeline'],
    ['fifteenDays', 'resources', 'resourceTimelineFifteenDays', 'timeline'],
    ['month', 'resources', 'resourceTimelineMonthCustom', 'timeline'],
    ['twoMonths', 'resources', 'resourceTimelineTwoMonths', 'timeline'],
    ['year', 'resources', 'resourceTimelineYearCustom', 'timeline'],
  ] as Array<[ProjectCalendarScope, 'calendar' | 'resources', string, string]>)(
    '%s %s shares %s with print',
    (scope, mode, key, kind) => {
      const view = projectCalendarViewDefinition(scope, mode);
      expect(view).toMatchObject({ key, kind });
      expect(view.options.duration).toEqual(projectCalendarScopes[scope].duration);
      if (scope === 'fifteenDays') expect(view.options.dateIncrement).toEqual({ weeks: 1 });
    },
  );
});
