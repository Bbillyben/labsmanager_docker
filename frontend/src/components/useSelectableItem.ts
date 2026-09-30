import { useEffect, useRef, useState, type MouseEvent, type KeyboardEvent } from 'react'

/** Shared row-selection behavior for compact, actionable detail lists. */
export function useSelectableItem() {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const containerRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    function clearOutside(event: PointerEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setSelectedId(null)
    }
    document.addEventListener('pointerdown', clearOutside)
    return () => document.removeEventListener('pointerdown', clearOutside)
  }, [])

  function rowProps(id: number, actionable: boolean) {
    return {
      tabIndex: actionable ? 0 : undefined,
      'data-selected': actionable ? selectedId === id : undefined,
      onClick: actionable ? (event: MouseEvent<HTMLElement>) => {
        if ((event.target as HTMLElement).closest('a, button, input, select, textarea')) return
        if (window.getSelection()?.toString()) return
        event.currentTarget.focus()
        setSelectedId(selectedId === id ? null : id)
      } : undefined,
      onKeyDown: actionable ? (event: KeyboardEvent<HTMLElement>) => {
        if (event.target !== event.currentTarget || !['Enter', ' '].includes(event.key)) return
        event.preventDefault()
        setSelectedId(selectedId === id ? null : id)
      } : undefined,
    }
  }

  return { selectedId, setSelectedId, containerRef, rowProps }
}
