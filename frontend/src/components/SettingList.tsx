import { useState } from 'react'
import type { SettingValue } from '../api/settings'
import type { UserSettingData } from '../api/userSettings'
import { normalizeMutationError } from '../api/errors'
import { useTranslation } from '../i18n/i18n'
import { SettingRow } from '../pages/SettingsHubPage'

function errorText(error: unknown, fallback: string) {
  const parsed = normalizeMutationError(error)
  return [...parsed.messages, ...Object.values(parsed.fields).flat()].join(' ') || fallback
}

export function SettingList({ settings, onChange, onReset }: {
  settings: UserSettingData[]
  onChange: (key: string, value: SettingValue) => Promise<UserSettingData>
  onReset?: (key: string) => Promise<UserSettingData>
}) {
  const { t } = useTranslation()
  const [values, setValues] = useState(settings)
  const [pending, setPending] = useState<string | null>(null)
  const [error, setError] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState<string | null>(null)
  async function run(key: string, operation: () => Promise<UserSettingData>) {
    setPending(key); setSaved(null); setError((old) => ({ ...old, [key]: '' }))
    try {
      const result = await operation()
      setValues((old) => old.map((row) => row.key === key ? result : row))
      setSaved(key)
      return result
    } catch (cause) {
      setError((old) => ({ ...old, [key]: errorText(cause, t('settings.saveError')) }))
      return null
    } finally { setPending(null) }
  }
  return <div>{values.map((setting) => <SettingRow key={setting.key} setting={setting} disabled={pending !== null} saving={pending === setting.key} saved={saved === setting.key} error={error[setting.key]} onSave={(value) => run(setting.key, () => onChange(setting.key, value))} onReset={onReset ? () => run(setting.key, () => onReset(setting.key)) : undefined} />)}</div>
}
