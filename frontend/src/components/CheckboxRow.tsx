import type { ComponentProps, ReactNode } from 'react'

type Props = Omit<ComponentProps<'input'>, 'type' | 'children'> & { children: ReactNode }

export function CheckboxRow({ children, ...input }: Props) {
  return <label className="flex min-h-9 cursor-pointer items-center gap-2 rounded-md px-1 text-sm leading-snug hover:bg-accent/50 has-[input:disabled]:cursor-not-allowed has-[input:disabled]:opacity-50">
    <input {...input} type="checkbox" className="size-4 shrink-0 accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" />
    <span className="min-w-0 break-words">{children}</span>
  </label>
}
