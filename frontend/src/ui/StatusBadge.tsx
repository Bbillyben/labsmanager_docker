import type { PropsWithChildren } from 'react'
import { Badge } from '../components/ui/badge'

const tones = {
  neutral: 'bg-muted text-muted-foreground',
  success: 'bg-success-surface text-success',
  warning: 'bg-warning-surface text-warning',
  danger: 'bg-destructive/10 text-destructive',
  info: 'bg-info-surface text-info',
}

export function StatusBadge({ children, tone = 'neutral' }: PropsWithChildren<{ tone?: keyof typeof tones }>) {
  return <Badge variant="secondary" className={tones[tone]}>{children}</Badge>
}
