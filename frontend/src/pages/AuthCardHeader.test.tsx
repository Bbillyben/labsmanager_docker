import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { I18nProvider } from '../i18n/I18nProvider'
import { AuthCardHeader } from './AuthCardHeader'

it.each([
  ['fr-FR', 'Accepter l’invitation', 'Créez votre compte pour rejoindre LabsManager.'],
  ['en-US', 'Reset your password', 'Enter your email address to receive a password reset link.'],
])('keeps the %s title and description beside the logo', (language, title, description) => {
  Object.defineProperty(window.navigator, 'languages', { configurable: true, value: [language] })
  render(<I18nProvider><AuthCardHeader title={title} titleId="auth-title" description={description} /></I18nProvider>)

  const heading = screen.getByRole('heading', { name: title })
  const header = heading.closest('header')
  expect(header).not.toBeNull()
  expect(heading).toHaveAttribute('id', 'auth-title')
  expect(heading.parentElement).toContainElement(within(header!).getByText(description))
  expect(within(header!).getByRole('img', { name: 'LabsManager' })).toHaveAttribute('src', `${import.meta.env.BASE_URL}labsmanager-logo.png`)
  expect(heading.parentElement).not.toContainElement(within(header!).getByRole('img', { name: 'LabsManager' }))
})
