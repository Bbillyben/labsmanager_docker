import { useState, type FormEvent, type RefObject } from 'react'
import { createOrganization, updateOrganization, createContact, updateContact, createOrganizationInfo, updateOrganizationInfo, createContactInfo, updateContactInfo, type Organization, type OrganizationKind, type Contact, type OrganizationInfo, type OrganizationOptions } from '../api/organizations'
import { normalizeMutationError } from '../api/errors'
import { useMutation } from '../api/useMutation'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '../components/ui/sheet'
import { useTranslation } from '../i18n/i18n'
import { Alert } from '../ui/Alert'
import { Button } from '../ui/Button'

type Common = { kind: OrganizationKind; organizationId?: string; onClose: () => void; onSaved: () => void; returnFocus: RefObject<HTMLElement | null> }
function ErrorMessage({ error }: { error: unknown }) {
  const parsed = error ? normalizeMutationError(error) : null
  return parsed ? <Alert tone="danger">{[...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ')}</Alert> : null
}
const fieldClass = 'h-9 w-full rounded-md border border-input bg-background px-3 text-sm'

export function OrganizationFormSheet({ kind, organization, onClose, onSaved, returnFocus }: Omit<Common, 'organizationId'> & { organization: Organization | null }) {
  const { t } = useTranslation()
  const [shortName, setShortName] = useState(organization?.short_name ?? '')
  const [name, setName] = useState(organization?.name ?? '')
  const mutation = useMutation()
  async function submit(event: FormEvent) {
    event.preventDefault()
    const result = await mutation.run(() => organization ? updateOrganization(kind, organization.id, { short_name: shortName, name }) : createOrganization(kind, { short_name: shortName, name }))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(organization ? 'organization.edit' : kind === 'institutions' ? 'organization.addInstitution' : 'organization.addFunder')}</SheetTitle><SheetDescription>{t('organization.formDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}><ErrorMessage error={mutation.error} />
      <label className="grid gap-1">{t('organization.shortName')}<input className={fieldClass} required maxLength={kind === 'institutions' ? 20 : 10} value={shortName} onChange={(event) => setShortName(event.target.value)} /></label>
      <label className="grid gap-1">{t('organization.name')}<input className={fieldClass} required maxLength={kind === 'institutions' ? 150 : 60} value={name} onChange={(event) => setName(event.target.value)} /></label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}

export function ContactFormSheet({ kind, organizationId, contact, options, onClose, onSaved, returnFocus }: Common & { organizationId: string; contact: Contact | null; options: OrganizationOptions }) {
  const { t } = useTranslation()
  const [firstName, setFirstName] = useState(contact?.first_name ?? '')
  const [lastName, setLastName] = useState(contact?.last_name ?? '')
  const [typeId, setTypeId] = useState(contact?.type.id ?? options.contact_types[0]?.id ?? 0)
  const [comment, setComment] = useState(contact?.comment ?? '')
  const mutation = useMutation()
  async function submit(event: FormEvent) {
    event.preventDefault()
    const data = { first_name: firstName, last_name: lastName, type_id: typeId, comment }
    const result = await mutation.run(() => contact ? updateContact(kind, organizationId, contact.id, data) : createContact(kind, organizationId, data))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(contact ? 'organization.editContact' : 'organization.addContact')}</SheetTitle><SheetDescription>{t('organization.contactDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}><ErrorMessage error={mutation.error} />
      <label className="grid gap-1">{t('organization.firstName')}<input className={fieldClass} required maxLength={50} value={firstName} onChange={(event) => setFirstName(event.target.value)} /></label>
      <label className="grid gap-1">{t('organization.lastName')}<input className={fieldClass} required maxLength={50} value={lastName} onChange={(event) => setLastName(event.target.value)} /></label>
      <label className="grid gap-1">{t('organization.contactType')}<select className={fieldClass} required value={typeId} onChange={(event) => setTypeId(Number(event.target.value))}>{options.contact_types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>
      <label className="grid gap-1">{t('organization.comment')}<textarea className={fieldClass} maxLength={350} value={comment} onChange={(event) => setComment(event.target.value)} /></label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || !typeId}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}

export function InfoFormSheet({ kind, organizationId, contactId, item, options, onClose, onSaved, returnFocus }: Common & { organizationId: string; contactId?: number; item: OrganizationInfo | null; options: OrganizationOptions }) {
  const { t } = useTranslation()
  const types = contactId === undefined ? options.organization_info_types : options.contact_info_types
  const [infoId, setInfoId] = useState(item?.info.id ?? types[0]?.id ?? 0)
  const [value, setValue] = useState(item?.value ?? '')
  const [comment, setComment] = useState(item?.comment ?? '')
  const mutation = useMutation()
  async function submit(event: FormEvent) {
    event.preventDefault()
    const data = { info_id: infoId, value, comment }
    const result = await mutation.run(() => contactId === undefined
      ? item ? updateOrganizationInfo(kind, organizationId, item.id, data) : createOrganizationInfo(kind, organizationId, data)
      : item ? updateContactInfo(kind, organizationId, contactId, item.id, data) : createContactInfo(kind, organizationId, contactId, data))
    if (result) onSaved()
  }
  return <Sheet open onOpenChange={(open) => { if (!open && !mutation.pending) onClose() }}><SheetContent finalFocus={returnFocus}>
    <SheetHeader><SheetTitle>{t(item ? 'organization.editInfo' : 'organization.addInfo')}</SheetTitle><SheetDescription>{t('organization.infoDescription')}</SheetDescription></SheetHeader>
    <form className="grid gap-4" onSubmit={(event) => void submit(event)}><ErrorMessage error={mutation.error} />
      <label className="grid gap-1">{t('organization.infoType')}<select className={fieldClass} required value={infoId} onChange={(event) => setInfoId(Number(event.target.value))}>{types.map((type) => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>
      <label className="grid gap-1">{t('organization.value')}<input className={fieldClass} maxLength={150} value={value} onChange={(event) => setValue(event.target.value)} /></label>
      <label className="grid gap-1">{t('organization.comment')}<textarea className={fieldClass} maxLength={contactId === undefined ? 350 : 150} value={comment} onChange={(event) => setComment(event.target.value)} /></label>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={onClose}>{t('common.cancel')}</Button><Button type="submit" disabled={mutation.pending || !infoId}>{t('common.save')}</Button></div>
    </form>
  </SheetContent></Sheet>
}
