/** Calendar widgets shared by the host and independently built plugins.
 *
 * Plugin builds should resolve these imports to the host entry so calendar
 * rendering uses the same React and FullCalendar instances as the core.
 */
export { default as FullCalendar } from '@fullcalendar/react'
export { default as dayGridPlugin } from '@fullcalendar/react/daygrid'
export { default as timeGridPlugin } from '@fullcalendar/react/timegrid'
export { default as interactionPlugin } from '@fullcalendar/react/interaction'
export { default as classicThemePlugin } from '@fullcalendar/react/themes/classic'
export { default as frLocale } from '@fullcalendar/react/locales/fr'
export { default as enGbLocale } from '@fullcalendar/react/locales/en-gb'
