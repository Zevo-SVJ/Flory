import { test, expect } from '@playwright/test'
import { safeNext } from '../lib/auth/redirects'

/**
 * `next` is attacker-controllable — it arrives in the query string of every
 * auth entry point. An unvalidated redirect target is how phishing links get
 * laundered through a trusted domain, so these cases are the security boundary.
 */

test.describe('safeNext', () => {
  test('keeps legitimate relative destinations, including the pasted URL', () => {
    expect(safeNext('/dashboard')).toBe('/dashboard')
    expect(safeNext('/history')).toBe('/history')
    expect(safeNext('/analyze?url=https%3A%2F%2Fexample.com%2Fthing')).toBe(
      '/analyze?url=https%3A%2F%2Fexample.com%2Fthing',
    )
  })

  test('rejects off-site redirects', () => {
    for (const hostile of [
      'https://evil.example/phish',
      'http://evil.example',
      '//evil.example',
      '///evil.example',
      'javascript:alert(1)',
      'data:text/html,<script>alert(1)</script>',
      '\\\\evil.example',
      '/\\evil.example',
    ]) {
      expect(safeNext(hostile), `${hostile} should not be honoured`).toBe('/dashboard')
    }
  })

  test('rejects empty and missing values', () => {
    expect(safeNext(null)).toBe('/dashboard')
    expect(safeNext(undefined)).toBe('/dashboard')
    expect(safeNext('')).toBe('/dashboard')
  })

  test('never bounces a signed-in user back into an auth page', () => {
    expect(safeNext('/login')).toBe('/dashboard')
    expect(safeNext('/signup?next=%2F')).toBe('/dashboard')
    expect(safeNext('/reset-password')).toBe('/dashboard')
    expect(safeNext('/auth/callback')).toBe('/dashboard')
  })

  test('honours a caller-supplied fallback', () => {
    expect(safeNext(null, '/settings')).toBe('/settings')
  })
})
