import type { CalendarEvent } from '../api/employees'
import type { GanttIdentity, LabsManagerGanttData } from './model'
import { SvarGanttAdapter, toSvarTasks, type GanttWindow } from './SvarGanttAdapter'
import { useTranslation } from '../i18n/i18n'
import styles from './LabsManagerGantt.module.css'

export function LabsManagerGantt({ data, events, window, onSelect, dark }: {
  data: LabsManagerGanttData
  events: CalendarEvent[]
  window: GanttWindow
  onSelect: (identity: GanttIdentity) => void
  dark: boolean
}) {
  const { t, language } = useTranslation()
  const { tasks, omitted } = toSvarTasks(data, events, window)
  if (!tasks.length) return <p className={styles.note}>{t('gantt.empty')}</p>
  return <>
    {omitted > 0 && <p className={styles.note}>{t('gantt.undated', { count: omitted })}</p>}
    <SvarGanttAdapter data={data} events={events} window={window} onSelect={onSelect} dark={dark} language={language} />
  </>
}
