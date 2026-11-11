import { AxiosError, AxiosHeaders } from 'axios'
import { describe, expect, it } from 'vitest'
import { isRateLimited } from './auth'

function httpError(status: number) {
  const config = { headers: new AxiosHeaders() }
  return new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, null, {
    status,
    statusText: '',
    headers: {},
    config,
    data: {},
  })
}

describe('isRateLimited', () => {
  it('recognises the login limiter response', () => {
    expect(isRateLimited(httpError(429))).toBe(true)
  })

  it('ignores other failures', () => {
    expect(isRateLimited(httpError(400))).toBe(false)
    expect(isRateLimited(new Error('Network Error'))).toBe(false)
  })
})
