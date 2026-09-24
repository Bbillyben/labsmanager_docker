import type { CalendarFilter, CalendarFilterValue } from '../api/employees'
import styles from './CalendarPluginFilters.module.css'

export type CalendarFilterValues = Record<string, CalendarFilterValue>

// Shared Calendar behavior is also consumed by the Employee Gantt.
// eslint-disable-next-line react-refresh/only-export-components
export function effectiveCalendarFilterValues(definitions: CalendarFilter[], values: CalendarFilterValues): Record<string, CalendarFilterValue> {
  return Object.fromEntries(definitions.map((definition) => {
    const selected = values[definition.id]
    if (selected !== undefined) return [definition.id, selected]
    if (definition.type === 'checkbox') return [definition.id, Array.isArray(definition.default) ? definition.default.map(String) : definition.choices.map((choice) => String(choice.value))]
    return [definition.id, definition.default ?? '']
  }))
}

export function CalendarPluginFilters({ definitions, onChange, values }: {
  definitions: CalendarFilter[]
  onChange: (values: CalendarFilterValues) => void
  values: CalendarFilterValues
}) {
  if (!definitions.length) return null
  const update = (id: string, value: CalendarFilterValue) => onChange({ ...values, [id]: value })
  return <div className={styles.filters}>
    {definitions.map((definition) => <CalendarPluginFilter definition={definition} key={definition.id} onChange={(value) => update(definition.id, value)} value={filterValue(definition, values)} />)}
  </div>
}

function CalendarPluginFilter({ definition, onChange, value }: {
  definition: CalendarFilter
  onChange: (value: CalendarFilterValue) => void
  value: CalendarFilterValue
}) {
  if (definition.type === 'select') return <label>{definition.title}<select onChange={(event) => onChange(event.target.value)} value={String(value)}>
    {!definition.choices.some((choice) => String(choice.value) === String(value)) && <option value="">—</option>}
    {definition.choices.map((choice) => <option key={String(choice.value)} value={String(choice.value)}>{choice.label}</option>)}
  </select></label>
  if (definition.type === 'radio') return <fieldset><legend>{definition.title}</legend><div className={styles.options}>
    {definition.choices.map((choice) => <label key={String(choice.value)}><input checked={String(value) === String(choice.value)} name={definition.id} onChange={() => onChange(String(choice.value))} type="radio" value={String(choice.value)} />{choice.label}</label>)}
  </div></fieldset>
  if (definition.type === 'checkbox') {
    const selected = Array.isArray(value) ? value.map(String) : []
    return <fieldset><legend>{definition.title}</legend><div className={styles.options}>
      {definition.choices.map((choice) => { const choiceValue = String(choice.value); return <label key={choiceValue}><input checked={selected.includes(choiceValue)} onChange={(event) => onChange(event.target.checked ? [...selected, choiceValue] : selected.filter((item) => item !== choiceValue))} type="checkbox" value={choiceValue} />{choice.label}</label> })}
    </div></fieldset>
  }
  return <label>{definition.title}<input onChange={(event) => onChange(event.target.value)} type={definition.type === 'input-color' ? 'color' : 'text'} value={String(value)} /></label>
}

function filterValue(definition: CalendarFilter, values: CalendarFilterValues): CalendarFilterValue {
  const value = values[definition.id]
  if (value !== undefined) return value
  if (definition.type === 'checkbox') return Array.isArray(definition.default) ? definition.default.map(String) : definition.choices.map((choice) => String(choice.value))
  return definition.default === null ? '' : definition.default
}
