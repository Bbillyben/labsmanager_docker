import type { ComponentProps } from 'react'
import { Button as ShadcnButton } from '../components/ui/button'

type Props = Omit<ComponentProps<typeof ShadcnButton>, 'variant'> & {
  variant?: ComponentProps<typeof ShadcnButton>['variant'] | 'primary'
}

// Compatibility for UX1 consumers; all rendering and variants belong to shadcn.
export function Button({ variant = 'secondary', type = 'button', ...props }: Props) {
  return <ShadcnButton type={type} variant={variant === 'primary' ? 'default' : variant} {...props} />
}
