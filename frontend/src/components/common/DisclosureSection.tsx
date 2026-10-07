import { ChevronDown } from 'lucide-react'
import { useId, useState, type ReactNode } from 'react'
import { Button } from '../../ui/Button'
import styles from './DisclosureSection.module.css'

type Props = {
  showLabel: string
  hideLabel: string
  children: ReactNode
}

export function DisclosureSection({ showLabel, hideLabel, children }: Props) {
  const [open, setOpen] = useState(false)
  const contentId = useId()
  const triggerId = useId()

  return <div className={styles.disclosure}>
    <Button id={triggerId} aria-controls={contentId} aria-expanded={open} variant="ghost" size="sm" className={styles.trigger} onClick={() => setOpen((value) => !value)}>
      <ChevronDown aria-hidden="true" className={styles.chevron} data-open={open} />
      {open ? hideLabel : showLabel}
    </Button>
    <div id={contentId} role="region" aria-labelledby={triggerId} hidden={!open}>{children}</div>
  </div>
}
