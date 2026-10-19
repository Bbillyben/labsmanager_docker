import { render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AuthBackground } from './AuthBackground'

afterEach(() => vi.restoreAllMocks())

it.each([
  [0, 1],
  [0.5, 2],
  [0.999, 3],
])('selects background %i from a random value of %f', (randomValue, backgroundNumber) => {
  vi.spyOn(Math, 'random').mockReturnValue(randomValue)
  render(<AuthBackground><p>Authentication</p></AuthBackground>)

  const background = screen.getByRole('main').style.backgroundImage
  expect(background).toContain('linear-gradient(145deg, rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.5))')
  expect(background).toContain(`url("${import.meta.env.BASE_URL}labsmanager-background_${backgroundNumber}.png")`)
  expect(background.match(/labsmanager-background_/g)).toHaveLength(1)
})

it('keeps the selected background when its contents change', () => {
  const random = vi.spyOn(Math, 'random').mockReturnValue(0)
  const { rerender } = render(<AuthBackground><p>Form</p></AuthBackground>)
  const background = screen.getByRole('main').style.backgroundImage

  random.mockReturnValue(0.999)
  rerender(<AuthBackground><p>Confirmation</p></AuthBackground>)

  expect(screen.getByRole('main').style.backgroundImage).toBe(background)
  expect(screen.getByText('Confirmation')).toBeInTheDocument()
  expect(random).toHaveBeenCalledTimes(1)
})
