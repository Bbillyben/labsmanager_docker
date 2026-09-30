import type { ViewOptions } from '@fullcalendar/react'

export type ProjectCalendarScope = 'fifteenDays' | 'month' | 'twoMonths' | 'year'

export const projectCalendarScopeOrder: ProjectCalendarScope[] = ['fifteenDays', 'month', 'twoMonths', 'year']

export const projectCalendarScopes = {
  fifteenDays: { label: 'projectCalendar.fifteenDays', calendarView: 'dayGridFifteenDays', resourceView: 'resourceTimelineFifteenDays', duration: { days: 15 } },
  month: { label: 'leaves.month', calendarView: 'dayGridMonthCustom', resourceView: 'resourceTimelineMonthCustom', duration: { months: 1 } },
  twoMonths: { label: 'projectCalendar.twoMonths', calendarView: 'dayGridTwoMonths', resourceView: 'resourceTimelineTwoMonths', duration: { months: 2 } },
  year: { label: 'leaves.year', calendarView: 'dayGridYearCustom', resourceView: 'resourceTimelineYearCustom', duration: { years: 1 } },
} as const

export const projectDayGridViews: Record<string, ViewOptions> = {
  dayGridFifteenDays: {
    type: 'dayGrid',
    dayMaxEvents: false,
    dayMaxEventRows: false,
    duration: projectCalendarScopes.fifteenDays.duration,
    dateIncrement: { weeks: 1 },

    dayHeaderFormat: {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    },
  },
  dayGridMonthCustom: {
    type: 'dayGrid', 
    duration: projectCalendarScopes.month.duration, 
    dateAlignment: 'month', 
    dayMaxEvents: false,
    dayMaxEventRows: false
  },
  dayGridTwoMonths: { 
    type: 'timeline', 
    duration: projectCalendarScopes.twoMonths.duration, 
    dateAlignment: 'month', 
    dayMaxEvents: false,
    dayMaxEventRows: false,
     slotHeaderFormat: [
      {
        month: 'long',
      },
      {
        weekday: 'short',
        day: 'numeric',
      },
    ],
  },
  dayGridYearCustom: {
    type: 'timeline',
    duration: projectCalendarScopes.year.duration,
    dayMaxEvents: false,
    dayMaxEventRows: false,
    dateIncrement: { years: 1 },
    slotDuration: {
      months: 1,
    },
    slotHeaderInterval: {
      months: 1,
    },
    slotHeaderFormat: [
      {
        month: 'long',
        week: 'short',
      },
    ],
  },
}

export const projectResourceViews: Record<string, ViewOptions> = {
  resourceTimelineFifteenDays: { 
    type: 'resourceTimeline', 
    duration: projectCalendarScopes.fifteenDays.duration,
    dateIncrement: { weeks: 1 },
    slotHeaderFormat: [
      {
        month: 'long',
      },
      {
        weekday: 'short',
        day: 'numeric',
      },
    ],

    slotDuration: {
      hours: 12,
    },

    slotHeaderInterval: {
      hours: 24,
    },
  },
  resourceTimelineMonthCustom: {
    type: 'resourceTimeline',
    duration: projectCalendarScopes.month.duration,
    dateIncrement: { weeks: 1 },

    slotDuration: {
      hours: 12,
    },

    slotHeaderInterval: {
      hours: 24,
    },

    slotHeaderFormat: [
      {
        month: 'long',
      },
      {
        weekday: 'short',
        day: 'numeric',
      },
    ],
  },

  resourceTimelineTwoMonths: { 
    type: 'resourceTimeline', 
    duration: projectCalendarScopes.twoMonths.duration, 
    dateAlignment: 'month',
    slotHeaderFormat: [
      {
        month: 'long',
      },
      {
        weekday: 'short',
        day: 'numeric',
      },
    ],
  },
  resourceTimelineYearCustom: {
    type: 'resourceTimeline',

    duration: projectCalendarScopes.year.duration,

    dateIncrement: { years: 1 },

    slotDuration: {
      months: 1,
    },

    slotHeaderInterval: {
      months: 1,
    },

    slotHeaderFormat: [
      {
        month: 'long',
        week: 'short',
      },
    ],
  },
}

function isoDate(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
}

export function projectCalendarRange(scope: ProjectCalendarScope, anchor: Date) {
  const year = anchor.getFullYear()
  const month = anchor.getMonth()
  const day = anchor.getDate()
  const start = scope === 'year' ? new Date(year, 0, 1) : scope === 'fifteenDays' ? new Date(year, month, day) : new Date(year, month, 1)
  const end = scope === 'fifteenDays' ? new Date(year, month, day + 14)
    : scope === 'month' ? new Date(year, month + 1, 0)
      : scope === 'twoMonths' ? new Date(year, month + 2, 0) : new Date(year, 11, 31)
  return { from: isoDate(start), to: isoDate(end) }
}

export function shiftProjectCalendarAnchor(anchor: Date, scope: ProjectCalendarScope, direction: number) {
  const year = anchor.getFullYear()
  const month = anchor.getMonth()
  if (scope === 'fifteenDays') return new Date(year, month, anchor.getDate() + 15 * direction)
  if (scope === 'year') return new Date(year + direction, 0, 1)
  return new Date(year, month + (scope === 'twoMonths' ? 2 : 1) * direction, 1)
}
