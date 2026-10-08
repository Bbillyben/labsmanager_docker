import { CalendarDays } from 'lucide-react'
import type { DashboardTimelineData, DashboardWidget } from '../api/dashboards'
import { Popover, PopoverContent, PopoverTitle, PopoverTrigger } from '../components/ui/popover'
import { useTranslation } from '../i18n/i18n'
import { genericInfoIcon } from '../pages/genericInfoIcons'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import { isTimeline, timelineDays } from './timelineData'
import styles from './CalendarGridRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }
type TimelineEvent = DashboardTimelineData['events'][number]

function markers(events: TimelineEvent[]) {
  const groups = new Map<string, { label: string; icon: string | undefined; count: number }>()
  for (const event of events) {
    const group = groups.get(event.source_type)
    if (group) group.count += 1
    else groups.set(event.source_type, { label: event.source_label, icon: event.icon, count: 1 })
  }
  return [...groups.entries()].map(([key, group]) => {
    const Icon = genericInfoIcon(group.icon ?? null)
    return <span key={key} className={styles.marker} aria-label={`${group.label}: ${group.count}`}>
      <Icon size={13} aria-hidden="true" /><span className={styles.markerLabel}>{group.label}</span><strong>{group.count}</strong>
    </span>
  })
}

export function CalendarGridRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isTimeline(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const data = widget.data
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const days = timelineDays(data.window_start, data.window_end)
  const offset = days.length ? (new Date(`${days[0]}T00:00:00Z`).getUTCDay() + 6) % 7 : 0
  const byDate = new Map<string, TimelineEvent[]>()
  for (const event of data.events) byDate.set(event.date, [...(byDate.get(event.date) ?? []), event])
  const weekdayLabels = Array.from({ length: 7 }, (_, index) => new Intl.DateTimeFormat(locale, { weekday: 'short', timeZone: 'UTC' }).format(new Date(Date.UTC(2026, 0, 5 + index))))
  const dayLabel = (day: string) => new Intl.DateTimeFormat(locale, { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' }).format(new Date(`${day}T00:00:00Z`))
  const stateLabel = (state: TimelineEvent['state']) => state === 'done' ? t('dashboard.timeline.state.done') : state === 'overdue' ? t('dashboard.timeline.state.overdue') : state === 'today' ? t('dashboard.timeline.state.today') : state === 'soon' ? t('dashboard.timeline.state.soon') : t('dashboard.timeline.state.future')

  return <div className={styles.calendar} data-size={size} data-mode={mode}>
    {data.earlier_overdue_count > 0 && <p className={styles.earlier}><CalendarDays size={15} aria-hidden="true" />{t('dashboard.timeline.earlierOverdue', { count: data.earlier_overdue_count })}</p>}
    <div className={styles.grid} aria-label={t('dashboard.timeline.calendar')}>
      {weekdayLabels.map((label, index) => <div key={index} className={styles.weekday}>{label}</div>)}
      {Array.from({ length: offset }, (_, index) => <div key={`pad-${index}`} className={styles.padding} aria-hidden="true" />)}
      {days.map((day) => {
        const events = byDate.get(day) ?? []
        const tone = events.some((item) => item.tone === 'danger') ? 'danger' : events.some((item) => item.tone === 'warning') ? 'warning' : 'neutral'
        const cell = <><span className={styles.dayHeading}><time dateTime={day} className={styles.date}>{Number(day.slice(-2))}</time>{day === data.today && <span className={styles.today}>{t('dashboard.timeline.today')}</span>}</span>{events.length > 0 && <span className={styles.markers}>{markers(events)}</span>}</>
        const attributes = { 'data-date': day, 'data-today': day === data.today, 'data-tone': tone }
        if (!events.length || mode === 'print') return <div key={day} className={styles.day} {...attributes}>{cell}</div>
        return <Popover key={day}>
          <PopoverTrigger className={`${styles.day} ${styles.dayButton}`} aria-label={t('dashboard.timeline.openDay', { date: dayLabel(day), count: events.length })} {...attributes}>{cell}</PopoverTrigger>
          <PopoverContent align="start" className={styles.popover}>
            <PopoverTitle>{dayLabel(day)}</PopoverTitle>
            <ul className={styles.detailList}>{events.map((event) => {
              const Icon = genericInfoIcon(event.icon ?? null)
              return <li key={event.id} className={styles.detail} data-tone={event.tone}>
                <span className={styles.detailType}><Icon size={14} aria-hidden="true" />{event.source_label} · {stateLabel(event.state)}</span>
                {event.href ? <a href={event.href}>{event.title}</a> : <strong>{event.title}</strong>}
                {event.project_name && <span>{event.project_name}</span>}
                {event.secondary && <span>{event.secondary}</span>}
              </li>
            })}</ul>
          </PopoverContent>
        </Popover>
      })}
    </div>
  </div>
}
