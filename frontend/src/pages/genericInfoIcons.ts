import { Badge, CircleQuestionMark, Columns3, Contact, Search, Stethoscope, type LucideIcon } from 'lucide-react'

const icons: Record<string, LucideIcon> = { Badge, Contact, Search, Columns3, Stethoscope }
export function genericInfoIcon(name: string | null): LucideIcon {
  return name && Object.hasOwn(icons, name) ? icons[name] : CircleQuestionMark
}
