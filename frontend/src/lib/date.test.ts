import { describe, expect, it } from 'vitest'

import { daysBetween, expiryStatus, formatDateKey, formatRelativeDays, parseDateKey } from './date'

const today = new Date(2026, 10, 11, 18, 30)

describe('date keys', () => {
  it('parses API dates as local days and formats them for the language', () => {
    expect(parseDateKey('2027-05-30').getDate()).toBe(30)
    expect(formatDateKey('2027-05-30', 'pt-PT')).toBe('30/05/2027')
    expect(formatDateKey('2027-05-30', 'en')).toBe('05/30/2027')
  })

  it('counts calendar days across the daylight saving change', () => {
    expect(daysBetween(new Date(2026, 9, 24, 23), new Date(2026, 9, 26, 0))).toBe(2)
    expect(daysBetween(today, new Date(2026, 10, 9))).toBe(-2)
  })
})

describe('expiry', () => {
  it('flags expired and same-day items as expired', () => {
    expect(expiryStatus('2026-11-09', today)).toEqual({ tone: 'expired', label: 'Expirou há 2 dias' })
    expect(expiryStatus('2026-11-10', today)).toEqual({ tone: 'expired', label: 'Expirou ontem' })
    expect(expiryStatus('2026-11-11', today)).toEqual({ tone: 'expired', label: 'Expira hoje' })
  })

  it('warns during the following week', () => {
    expect(expiryStatus('2026-11-12', today)).toEqual({ tone: 'soon', label: 'Expira amanhã' })
    expect(expiryStatus('2026-11-14', today)).toEqual({ tone: 'soon', label: 'Expira em 3 dias' })
    expect(expiryStatus('2026-11-18', today).tone).toBe('soon')
  })

  it('shows the date when expiry is far away', () => {
    expect(expiryStatus('2026-11-19', today)).toEqual({ tone: 'later', label: 'Validade: 19/11/2026' })
  })
})

const now = new Date(2026, 10, 11, 9, 30)

describe('formatRelativeDays', () => {
  it('counts calendar days in local time, not elapsed hours', () => {
    expect(formatRelativeDays(new Date(2026, 10, 10, 23, 50).toISOString(), now, 'pt-PT')).toBe('ontem')
    expect(formatRelativeDays(new Date(2026, 10, 11, 0, 5).toISOString(), now, 'pt-PT')).toBe('hoje')
  })

  it('localises the phrase for the requested language', () => {
    expect(formatRelativeDays(new Date(2026, 10, 8).toISOString(), now, 'pt-PT')).toBe('há 3 dias')
    expect(formatRelativeDays(new Date(2026, 10, 8).toISOString(), now, 'en')).toBe('3 days ago')
  })

  it('switches to weeks, months and years for older dates', () => {
    expect(formatRelativeDays(new Date(2026, 9, 28).toISOString(), now, 'pt-PT')).toBe('há 2 semanas')
    expect(formatRelativeDays(new Date(2026, 7, 1).toISOString(), now, 'en')).toBe('3 months ago')
    expect(formatRelativeDays(new Date(2024, 10, 1).toISOString(), now, 'en')).toBe('2 years ago')
  })
})
