import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { CalendarEvent } from '../api/employees'
import { useTranslation } from '../i18n/i18n'
import { PrintButton } from '../print/PrintButton'
import type { GanttPrintState } from '../print/GanttPrintView'
import { Button } from '../ui/Button'
import { LabsManagerGantt } from './LabsManagerGantt'
import type { GanttIdentity, LabsManagerGanttData } from './model'
import { planningWindow, type PlanningMonths } from './planningWindow'
import styles from './EmployeeGanttPanel.module.css'

export function PlanningGanttView({ data, events, anchor, months, onAnchorChange, onMonthsChange, onSelect, printTitle, printFilters, showPrint = true }: {
  data: LabsManagerGanttData | null
  events: CalendarEvent[]
  anchor: Date
  months: PlanningMonths
  onAnchorChange: (date: Date) => void
  onMonthsChange: (months: PlanningMonths) => void
  onSelect: (identity: GanttIdentity) => void
  printTitle?: string
  printFilters?: Record<string, unknown>
  showPrint?: boolean
}) {
  const { language, t } = useTranslation()
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const [closedKeys, setClosedKeys] = useState<Set<string>>(() => new Set())
  const window = planningWindow(anchor, months)
  useEffect(() => {
    const observer = new MutationObserver(() => setDark(document.documentElement.classList.contains('dark')))
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])
  const step = months === 6 ? 3 : months === 12 ? 6 : months === 120 ? 24 : 12
  const move = (direction: number) => onAnchorChange(new Date(anchor.getFullYear(), anchor.getMonth() + direction * step, 1))
  const format = (value: string) => new Intl.DateTimeFormat(language, { month: 'short', year: 'numeric' }).format(new Date(`${value}T12:00:00`))

  return <div className={styles.root}>
    <div className={styles.toolbar}><div className={styles.group}>
      <Button aria-label={t('gantt.previous')} onClick={() => move(-1)} size="icon-sm" variant="ghost"><ChevronLeft aria-hidden="true" /></Button>
      <Button onClick={() => onAnchorChange(new Date())} size="sm" variant="ghost">{t('gantt.current')}</Button>
      <Button aria-label={t('gantt.next')} onClick={() => move(1)} size="icon-sm" variant="ghost"><ChevronRight aria-hidden="true" /></Button>
      <strong>{format(window.from)} – {format(window.to)}</strong>
    </div><div aria-label={t('gantt.period')} className={styles.group} role="group">
      {([6, 12, 24, 60, 120] as const).map((value) => <Button aria-pressed={months === value} key={value} onClick={() => onMonthsChange(value)} size="sm" variant={months === value ? 'secondary' : 'ghost'}>{t(`gantt.months${value}`)}</Button>)}
    </div>{data && showPrint && <PrintButton createRequest={() => ({ renderer: 'gantt', title: printTitle ?? t('calendars.projects'), state: { data, events, window, filters: printFilters, closedKeys: [...closedKeys] } satisfies GanttPrintState })} />}</div>
    {data && <LabsManagerGantt data={data} events={events} dark={dark} window={window} onSelect={onSelect} closedKeys={closedKeys} onOpenChange={(key, open) => setClosedKeys((previous) => { const next = new Set(previous); if (open) next.delete(key); else next.add(key); return next })} />}
  </div>
}
