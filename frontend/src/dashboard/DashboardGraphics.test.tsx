import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { RatioGauge, RoundedProgressGauge, VerticalStackedMetric } from './DashboardGraphics'

it('renders a rounded gauge with its true value, tone and secondary text beyond 100%', () => {
  const view = render(<RoundedProgressGauge label="Funding" value={112} displayValue="112%" tone="danger" secondary="Overspent" />)
  expect(screen.getByText('112%')).toBeInTheDocument()
  expect(screen.getByText('Overspent')).toBeInTheDocument()
  expect(screen.getByRole('progressbar', { name: 'Funding' })).toHaveAttribute('value', '100')
  expect(view.container.firstChild).toHaveAttribute('data-tone', 'danger')
})

it('renders a stacked metric with explicit segment counts and an accessible equivalent', () => {
  render(<VerticalStackedMetric label="Milestones" total={12} summary="2 overdue" showLegend segments={[
    { key: 'upcoming', value: 7, tone: 'success', label: 'upcoming' },
    { key: 'imminent', value: 3, tone: 'info', label: 'imminent' },
    { key: 'overdue', value: 2, tone: 'danger', label: 'overdue' },
  ]} />)
  expect(screen.getByRole('img', { name: '12 Milestones: 7 upcoming, 3 imminent, 2 overdue' })).toBeInTheDocument()
  expect(screen.getAllByText('2 overdue')).toHaveLength(2)
  expect(screen.getByText('3 imminent')).toBeInTheDocument()
})

it('positions a ratio marker against the target while keeping numeric labels visible', () => {
  const view = render(<RatioGauge label="Funding pace" value={0.82} target={1} domain={[0, 2]}
    displayValue="0.82" targetLabel="target" leftLabel="0" rightLabel="2+" tone="success" />)
  expect(screen.getByRole('img', { name: 'Funding pace: 0.82; target: 1' })).toBeInTheDocument()
  expect(screen.getByText('0.82')).toBeInTheDocument()
  expect(view.container.querySelector('[class*="ratioMarker"]')).toHaveStyle({ left: '41%' })
  expect(view.container.querySelector('[class*="ratioTarget"]')).toHaveStyle({ left: '50%' })
})
