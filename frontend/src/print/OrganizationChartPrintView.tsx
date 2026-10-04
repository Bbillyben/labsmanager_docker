import { useEffect, useState } from 'react'
import { useTranslation } from '../i18n/i18n'
import type { OrganizationGraph } from '../pages/organizationGraph'
import { layoutOrganizationGraph, NODE_HEIGHT, NODE_WIDTH } from '../pages/organizationLayout'
import type { PrintRendererProps } from './registry'
import styles from './print.module.css'

export type OrganizationChartPrintState = { graph: OrganizationGraph; showCurrentOnly: boolean; search: string; focusId?: number | null }

export function OrganizationChartPrintView({ state, onReady }: PrintRendererProps<OrganizationChartPrintState>) {
  const { t } = useTranslation()
  const [layout, setLayout] = useState<Awaited<ReturnType<typeof layoutOrganizationGraph>> | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    let active = true
    layoutOrganizationGraph(state.graph).then((result) => { if (active) { setLayout(result); onReady() } }, () => { if (active) setError(true) })
    return () => { active = false }
  }, [state.graph, onReady])
  if (error) return <p role="alert">{t('print.layoutError')}</p>
  if (!layout) return null
  const width = Math.max(1, ...layout.nodes.map((node) => node.position.x + NODE_WIDTH))
  const height = Math.max(1, ...layout.nodes.map((node) => node.position.y + NODE_HEIGHT))
  const byId = new Map(layout.nodes.map((node) => [node.id, node]))
  return <section className={styles.content} data-testid="organization-chart-print">
    <svg className={styles.organization} viewBox={`-15 -15 ${width + 30} ${height + 30}`} role="img" aria-label="Organization chart">
      {layout.edges.map((edge) => { const source = byId.get(edge.source); const target = byId.get(edge.target); return source && target ? <path key={edge.id} d={`M${source.position.x + NODE_WIDTH / 2} ${source.position.y + NODE_HEIGHT} V${(source.position.y + NODE_HEIGHT + target.position.y) / 2} H${target.position.x + NODE_WIDTH / 2} V${target.position.y}`} fill="none" stroke="#67748a" strokeWidth="2" /> : null })}
      {layout.nodes.map((node) => { const employee = node.data.employee as { id: number; name: string; statuses: { name: string }[] }; return <g key={node.id} transform={`translate(${node.position.x},${node.position.y})`}>
        <rect width={NODE_WIDTH} height={NODE_HEIGHT} rx="8" fill="#fff" stroke={state.focusId === employee.id ? '#1565c0' : '#8c98a7'} strokeWidth={state.focusId === employee.id ? 3 : 1} />
        <text x="10" y="34" fontSize="14" fontWeight="bold">{employee.name}</text>
        <text x="10" y="58" fontSize="11">{employee.statuses.map((status) => status.name).join(' · ')}</text>
      </g> })}
    </svg>
  </section>
}
