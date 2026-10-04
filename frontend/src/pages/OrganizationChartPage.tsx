import { Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider, useReactFlow, type Edge, type Node, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { ChevronDown, ChevronRight, LocateFixed, Search } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOrganizationChart, setOrganizationChartScope, type ChartEmployee, type OrganizationChart } from '../api/organizationChart'
import { ApiError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { PrintButton } from '../print/PrintButton'
import type { OrganizationChartPrintState } from '../print/OrganizationChartPrintView'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'
import { PageHeader } from '../ui/PageHeader'
import { buildOrganizationGraph, organizationHighlight, type OrganizationHighlight } from './organizationGraph'
import { layoutOrganizationGraph, NODE_HEIGHT, NODE_WIDTH } from './organizationLayout'
import styles from './OrganizationChartPage.module.css'

type EmployeeNodeData = {
  employee: ChartEmployee
  expandable: boolean
  collapsed: boolean
  highlight: OrganizationHighlight
  isolated: boolean
  onToggle: (id: number) => void
  expandLabel: string
  collapseLabel: string
}

function EmployeeNode({ data }: NodeProps) {
  const { employee, expandable, collapsed, highlight, isolated, onToggle, expandLabel, collapseLabel } = data as EmployeeNodeData
  return <div className={`${styles.node} nopan`} data-highlight={highlight} data-inactive={!employee.is_active} data-isolated={isolated}>
    <Handle type="target" position={Position.Top} isConnectable={false} />
    <div className={styles.nodeMain}>
      <div className={styles.nodeText}>
        {employee.can_view ? <Link className="nodrag nopan" to={`/employees/${employee.id}`} onMouseDown={(event) => event.stopPropagation()} onClick={(event) => event.stopPropagation()}>{employee.name}</Link> : <span>{employee.name}</span>}
        <span className={styles.status}>{employee.statuses.map((status) => status.name).join(' · ')}</span>
      </div>
      {expandable && <button type="button" className={`${styles.toggle} nodrag nopan`} onMouseDown={(event) => event.stopPropagation()} onClick={(event) => { event.stopPropagation(); onToggle(employee.id) }} aria-label={`${collapsed ? expandLabel : collapseLabel} ${employee.name}`} aria-expanded={!collapsed}>
        {collapsed ? <ChevronRight size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
      </button>}
    </div>
    <Handle type="source" position={Position.Bottom} isConnectable={false} />
  </div>
}

const nodeTypes = { employee: EmployeeNode }

function ChartContent() {
  const { t } = useTranslation()
  const flow = useReactFlow()
  const [chart, setChart] = useState<OrganizationChart | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [saving, setSaving] = useState(false)
  const [revision, setRevision] = useState(0)
  const [collapsed, setCollapsed] = useState<Set<number>>(() => new Set())
  const [search, setSearch] = useState('')
  const [focusedId, setFocusedId] = useState<number | null>(null)
  const [layout, setLayout] = useState<{ nodes: Node[]; edges: Edge[] }>({ nodes: [], edges: [] })
  const fittedChart = useRef<OrganizationChart | null>(null)
  const graph = useMemo(() => buildOrganizationGraph(chart?.employees ?? [], chart?.relationships ?? [], collapsed, search), [chart, collapsed, search])

  useEffect(() => {
    const controller = new AbortController()
    getOrganizationChart(controller.signal).then(
      (result) => { if (!controller.signal.aborted) { setChart(result); setError(null) } },
      (cause: unknown) => { if (!controller.signal.aborted) { setChart(null); setError(cause) } },
    )
    return () => controller.abort()
  }, [revision])

  useEffect(() => {
    let active = true
    layoutOrganizationGraph(graph).then((result) => {
      if (!active) return
      setLayout(result)
      if (chart && chart !== fittedChart.current) {
        fittedChart.current = chart
        requestAnimationFrame(() => { if (active) void flow.fitView({ padding: 0.16, maxZoom: 1 }) })
      }
    }, (cause: unknown) => { if (active) setError(cause) })
    return () => { active = false }
  }, [graph, flow, chart])

  function toggle(id: number) {
    setCollapsed((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function changeScope(showCurrentOnly: boolean) {
    setSaving(true)
    try {
      await setOrganizationChartScope(showCurrentOnly)
      setCollapsed(new Set())
      setRevision((value) => value + 1)
    } catch (cause) { setError(cause) }
    finally { setSaving(false) }
  }

  function focus(id: number) {
    setFocusedId(id)
    const node = layout.nodes.find((item) => item.id === String(id))
    if (node) void flow.setCenter(node.position.x + NODE_WIDTH / 2, node.position.y + NODE_HEIGHT / 2, { zoom: 1, duration: 400 })
  }

  const displayedNodes = layout.nodes.map((node) => {
    const employee = node.data.employee as ChartEmployee
    return { ...node, data: {
      employee,
      expandable: graph.expandable.has(employee.id),
      collapsed: collapsed.has(employee.id),
      highlight: organizationHighlight(graph, employee.id),
      isolated: graph.isolated.has(employee.id),
      onToggle: toggle,
      expandLabel: t('organizationChart.expand'),
      collapseLabel: t('organizationChart.collapse'),
    } }
  })
  const matches = graph.employees.filter((employee) => graph.matches.has(employee.id))

  return <>
    <PageHeader title={t('organizationChart.title')} description={t('organizationChart.description')} />
    <div className={styles.toolbar}>
      <label className={styles.search}><Search size={17} aria-hidden="true" /><span className="sr-only">{t('organizationChart.search')}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('organizationChart.search')} /></label>
      <label className={styles.scope}><input type="checkbox" checked={chart?.show_current_only ?? true} disabled={!chart || saving} onChange={(event) => void changeScope(event.target.checked)} />{t('organizationChart.currentOnly')}</label>
      <Button variant="outline" onClick={() => void flow.fitView({ padding: 0.16, maxZoom: 1 })}><LocateFixed size={16} aria-hidden="true" />{t('organizationChart.fit')}</Button>
      {chart && <PrintButton createRequest={() => ({ renderer: 'organization-chart', title: t('organizationChart.title'), state: { graph, showCurrentOnly: chart.show_current_only, search, focusId: focusedId } satisfies OrganizationChartPrintState })} />}
    </div>
    {!!error && <Alert tone="danger">{error instanceof ApiError && error.status === 409 ? t('organizationChart.cycleError') : t('organizationChart.loadError')} <Button onClick={() => setRevision((value) => value + 1)}>{t('common.retry')}</Button></Alert>}
    {!error && !chart && <p role="status">{t('common.loading')}</p>}
    {chart && search.trim() && <div className={styles.results} role="status">{t('organizationChart.matches', { count: matches.length })}{matches.map((employee) => <Button key={employee.id} variant="ghost" onClick={() => focus(employee.id)}>{employee.name}</Button>)}</div>}
    {chart && !chart.employees.length && <p>{t('organizationChart.empty')}</p>}
    {chart && !!chart.employees.length && <div className={styles.canvas} aria-label={t('organizationChart.title')}>
      <ReactFlow nodes={displayedNodes} edges={layout.edges} nodeTypes={nodeTypes} nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} fitView minZoom={0.1} maxZoom={2} proOptions={{ hideAttribution: true }}>
        <Background /><Controls showInteractive={false} />
      </ReactFlow>
    </div>}
  </>
}

export function OrganizationChartPage() {
  return <ReactFlowProvider><ChartContent /></ReactFlowProvider>
}
