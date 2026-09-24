import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { CalendarFilter } from '../api/employees'
import { CalendarPluginFilters } from './CalendarPluginFilters'

const definitions: CalendarFilter[] = [
  { id: 'sample-select', title: 'Select value', type: 'select', source: 'sample', choices: [{ value: 'a', label: 'A' }, { value: 'b', label: 'B' }], default: 'a' },
  { id: 'sample-check', title: 'Check values', type: 'checkbox', source: 'sample', choices: [{ value: 'x', label: 'X' }, { value: 'y', label: 'Y' }], default: ['x'] },
  { id: 'sample-radio', title: 'Radio value', type: 'radio', source: 'sample', choices: [{ value: 'r1', label: 'R1' }, { value: 'r2', label: 'R2' }], default: 'r1' },
  { id: 'sample-text', title: 'Text value', type: 'input-text', source: 'sample', choices: [], default: 'hello' },
  { id: 'sample-color', title: 'Color value', type: 'input-color', source: 'sample', choices: [], default: '#112233' },
]

describe('CalendarPluginFilters', () => {
  it('renders every normalized type and reports opaque ids and values', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<CalendarPluginFilters definitions={definitions} onChange={onChange} values={{}} />)

    expect(screen.getByLabelText('Select value')).toHaveValue('a')
    expect(screen.getByLabelText('X')).toBeChecked()
    expect(screen.getByLabelText('R1')).toBeChecked()
    expect(screen.getByLabelText('Text value')).toHaveValue('hello')
    expect(screen.getByLabelText('Color value')).toHaveValue('#112233')

    await user.selectOptions(screen.getByLabelText('Select value'), 'b')
    expect(onChange).toHaveBeenCalledWith({ 'sample-select': 'b' })
    await user.click(screen.getByLabelText('Y'))
    expect(onChange).toHaveBeenCalledWith({ 'sample-check': ['x', 'y'] })
    await user.click(screen.getByLabelText('R2'))
    expect(onChange).toHaveBeenCalledWith({ 'sample-radio': 'r2' })
  })
})
