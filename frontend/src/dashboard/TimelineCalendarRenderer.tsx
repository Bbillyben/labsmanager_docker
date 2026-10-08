import type { CSSProperties } from 'react'
import { CalendarDays } from 'lucide-react'
import type { DashboardTimelineData, DashboardWidget } from '../api/dashboards'
import { useTranslation } from '../i18n/i18n'
import { genericInfoIcon } from '../pages/genericInfoIcons'
import type { DashboardMode } from './mode'
import type { DashboardSize } from './size'
import { isTimeline, timelineDays } from './timelineData'
import styles from './TimelineCalendarRenderer.module.css'

type Props = { widget: DashboardWidget; size: DashboardSize; mode?: DashboardMode }

export function TimelineCalendarRenderer({ widget, size, mode = 'view' }: Props) {
  const { t, language } = useTranslation()
  if (!isTimeline(widget.data)) return <p className="muted-text">{t('dashboard.emptyWidget')}</p>
  const data = widget.data
  const locale = language === 'fr' ? 'fr-FR' : 'en-GB'
  const days = timelineDays(data.window_start, data.window_end)
  const byDate = new Map<string, DashboardTimelineData['events']>()
  for (const event of data.events) byDate.set(event.date, [...(byDate.get(event.date) ?? []), event])
  return <div className={styles.timeline} data-size={size} data-mode={mode}>
    {data.earlier_overdue_count > 0 && <p className={styles.earlier}><CalendarDays size={15} aria-hidden="true" />{t('dashboard.timeline.earlierOverdue', { count: data.earlier_overdue_count })}</p>}
    <div className={styles.scroll} aria-label={t('dashboard.timeline.calendar')}>
      <div className={styles.days} style={{ '--timeline-days': days.length } as CSSProperties}>
        {days.map((day) => <section key={day} className={styles.day} data-today={day === data.today}>
          <h4><time dateTime={day}>{new Intl.DateTimeFormat(locale, { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(`${day}T00:00:00Z`))}</time>{day === data.today && <span>{t('dashboard.timeline.today')}</span>}</h4>
          {(byDate.get(day) ?? []).map((event) => {
            const Icon = genericInfoIcon(event.icon ?? null)
            return <article key={event.id} className={styles.event} data-tone={event.tone}>
            <span className={styles.source}><Icon size={13} aria-hidden="true" />{event.source_label}</span>
            {mode === 'print' || !event.href ? <strong>{event.title}</strong> : <a href={event.href}>{event.title}</a>}
            {size !== 'compact' && event.project_name && <span className={styles.project}>{mode === 'print' || !event.project_href ? event.project_name : <a href={event.project_href}>{event.project_name}</a>}</span>}
            {(size === 'expanded' || mode === 'print') && event.secondary && <span className={styles.secondary}>{event.secondary}</span>}
            <span className={styles.state}>{event.state === 'done' ? t('dashboard.timeline.state.done') : event.state === 'overdue' ? t('dashboard.timeline.state.overdue') : event.state === 'today' ? t('dashboard.timeline.state.today') : event.state === 'soon' ? t('dashboard.timeline.state.soon') : t('dashboard.timeline.state.future')}</span>
          </article>})}
        </section>)}
      </div>
    </div>
  </div>
}
