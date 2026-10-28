import { useState } from 'react'
import { EntitySearch, employeeFilterSources, PLUGIN_UI_API_VERSION } from '@labsmanager/plugin-ui'
import './style.css'

type Context = { entity?: string; objectId?: number }
type Props = { context: Context }

function EmployeePicker() {
  const [employeeId, setEmployeeId] = useState('')
  return <div className="model-example-picker">
    <label htmlFor="model-example-employee">Employé</label>
    <EntitySearch id="model-example-employee" label="Employé" value={employeeId}
      source={employeeFilterSources.employees} onChange={setEmployeeId} />
    <p>Employé sélectionné : <strong>{employeeId || 'aucun'}</strong></p>
  </div>
}

function Counter() {
  const [count, setCount] = useState(0)
  return <button className="model-example-button" type="button" onClick={() => setCount((value) => value + 1)}>
    Interactions React : {count}
  </button>
}

export function Page({ context: _context }: Props) {
  return <section className="model-example">
    <h1>Model Example</h1>
    <p>Interface React externe · API LabsManager v{PLUGIN_UI_API_VERSION}</p>
    <EmployeePicker />
    <Counter />
  </section>
}

export function EmployeeTab({ context }: Props) {
  return <section className="model-example">
    <h2>Model Example · Employé</h2>
    <p>Contexte autorisé : {context.entity} #{context.objectId}</p>
    <EmployeePicker />
    <Counter />
  </section>
}
