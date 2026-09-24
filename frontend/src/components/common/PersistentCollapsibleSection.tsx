import { ChevronDown, ChevronRight } from 'lucide-react'
import { useId, useState, type PropsWithChildren } from 'react'
import { useTranslation } from '../../i18n/i18n'
import { Button } from '../../ui/Button'
import styles from './PersistentCollapsibleSection.module.css'

type Props = PropsWithChildren<{
  storageKey: string
  title: string
}>

export function PersistentCollapsibleSection({ children, storageKey, title }: Props) {
  const { t } = useTranslation()
  const contentId = useId()
  const triggerId = useId()
  const [open, setOpen] = useState(() => {
    try { return localStorage.getItem(storageKey) !== 'false' } catch { return true }
  })

  function toggle() {
    const next = !open
    setOpen(next)
    try { localStorage.setItem(storageKey, String(next)) } catch { /* Persistence is optional. */ }
  }

  return <section className={styles.section}>
    <h2 className={styles.heading}>
      <Button
        aria-controls={contentId}
        aria-expanded={open}
        aria-label={t(open ? 'section.collapse' : 'section.expand', { title })}
        className={styles.trigger}
        id={triggerId}
        onClick={toggle}
        variant="ghost"
      ><span>{title}</span>{open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}</Button>
    </h2>
    {open && <div aria-labelledby={triggerId} id={contentId} role="region">{children}</div>}
  </section>
}
