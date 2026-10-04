import { CopyableValue } from './common/CopyableValue'
import { useTranslation } from '../i18n/i18n'
import { typedInfoHref, type InfoKind } from './typedInfoLinks'

export function TypedInfoValue({ kind, value, mapProvider }: { kind: InfoKind; value: string | null; mapProvider: 'gmap' | 'opensm' }) {
  const { t } = useTranslation()
  const href = typedInfoHref(kind, value, mapProvider)
  const label = kind === 'tel' ? t('organization.call') : kind === 'mail' ? t('organization.email') : kind === 'addr' ? t('organization.map') : t('organization.openLink')
  return <CopyableValue value={value}>{href ? <a href={href} aria-label={`${label}: ${value}`} target={kind === 'link' || kind === 'addr' ? '_blank' : undefined} rel={kind === 'link' || kind === 'addr' ? 'noreferrer' : undefined}>{value}</a> : value || '—'}</CopyableValue>
}
