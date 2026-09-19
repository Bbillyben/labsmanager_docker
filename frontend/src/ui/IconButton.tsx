import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Button } from './Button'

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'aria-label' | 'children'> & {
  label: string
  children: ReactNode
}

export function IconButton({ children, label, ...props }: IconButtonProps) {
  return <Button aria-label={label} title={label} variant="ghost" size="icon" {...props}>{children}</Button>
}
