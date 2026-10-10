import { Check, Copy } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useTranslation } from '../../i18n/i18n'
import { Button } from '../../ui/Button'
import { writeToClipboard } from '../../utils/clipboard'
import styles from './CopyableValue.module.css'

type Props = {
  value: string | null | undefined
  children?: ReactNode
}

export function CopyableValue({ value, children }: Props) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const timeout = useRef<number | undefined>(undefined)
  const copyable = value !== null && value !== undefined && value !== ''

  useEffect(() => () => window.clearTimeout(timeout.current), [])

  async function copy() {
    if (!copyable) return
    if (await writeToClipboard(value)) {
      setCopied(true)
      window.clearTimeout(timeout.current)
      timeout.current = window.setTimeout(() => setCopied(false), 1600)
    } else {
      setCopied(false)
    }
  }

  return <span className={styles.value}>
    <span className={styles.content}>{children ?? value ?? '—'}</span>
    {copyable && <Button
      aria-label={copied ? t('copy.copied') : t('copy.copy')}
      className={styles.copy}
      onClick={() => void copy()}
      size="icon-xs"
      title={copied ? t('copy.copied') : t('copy.copy')}
      variant="ghost"
    >{copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}</Button>}
  </span>
}
