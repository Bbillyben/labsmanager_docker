import type { ComponentProps } from 'react'

export function SelectableTableRow({ rowId, selectedId, onSelect, ...props }: Omit<ComponentProps<'tr'>, 'onClick' | 'onKeyDown' | 'onSelect'> & {
  rowId: number
  selectedId: number | null
  onSelect: (id: number | null) => void
}) {
  return <tr {...props} tabIndex={0} aria-selected={selectedId === rowId} data-selected={selectedId === rowId}
    onClick={(event) => {
      if (!event.currentTarget.contains(event.target as Node) || (event.target as HTMLElement).closest('a, button, input, select, textarea')) return
      if (window.getSelection()?.toString()) return
      event.currentTarget.focus()
      onSelect(selectedId === rowId ? null : rowId)
    }}
    onKeyDown={(event) => {
      if (event.target !== event.currentTarget || (event.key !== 'Enter' && event.key !== ' ')) return
      event.preventDefault()
      onSelect(selectedId === rowId ? null : rowId)
    }} />
}
