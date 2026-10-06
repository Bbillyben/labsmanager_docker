import { Badge, BadgeDollarSign, BookOpen, BookUser, Bookmark, Building2, CalendarDays, CircleQuestionMark, Cloud, Columns3, Contact, Dna, FileSignature, Flag, FolderKanban, IdCard, Landmark, Link, Mail, MapPin, Phone, PiggyBank, Printer, Receipt, Search, Signpost, Stethoscope, UserRound, UserRoundCheck, UsersRound, Wallet, type LucideIcon } from 'lucide-react'

const icons: Record<string, LucideIcon> = { Badge, Contact, Search, Columns3, Stethoscope, Landmark, BookOpen, Bookmark, Cloud, UserRoundCheck, UserRound, FolderKanban, FileSignature, UsersRound, Signpost, Dna, PiggyBank, BookUser, Flag, Printer, BadgeDollarSign, IdCard, Building2, Phone, Link, MapPin, Mail, Wallet, Receipt, CalendarDays }
export function genericInfoIcon(name: string | null): LucideIcon {
  return name && Object.hasOwn(icons, name) ? icons[name] : CircleQuestionMark
}
