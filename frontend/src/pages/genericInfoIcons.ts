import { Badge, BookOpen, Bookmark, CircleQuestionMark, Cloud, Columns3, Contact, Landmark, Search, Stethoscope, UserRoundCheck, type LucideIcon } from 'lucide-react'

const icons: Record<string, LucideIcon> = { Badge, Contact, Search, Columns3, Stethoscope, Landmark, BookOpen, Bookmark, Cloud, UserRoundCheck }
export function genericInfoIcon(name: string | null): LucideIcon {
  return name && Object.hasOwn(icons, name) ? icons[name] : CircleQuestionMark
}
