import { describe, expect, it } from 'vitest'
import { passwordResetBridgeUrl } from './resetBridge'

describe('password reset bridge', () => {
  it('uses the same-origin API proxy and encodes the token path segment', () => {
    expect(passwordResetBridgeUrl('uid-token')).toBe('/api/v1/auth/password/reset/bridge/uid-token/')
    expect(passwordResetBridgeUrl('uid/token')).toBe('/api/v1/auth/password/reset/bridge/uid%2Ftoken/')
  })
})
