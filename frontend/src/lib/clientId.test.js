import { describe, expect, test } from 'vitest'
import { createClientId } from './clientId'

describe('client ID generation', () => {
  test('uses randomUUID in secure browser contexts', () => {
    expect(createClientId({ randomUUID: () => 'secure-id' })).toBe('secure-id')
  })

  test('creates a UUID-compatible ID on LAN HTTP origins', () => {
    const cryptoWithoutRandomUUID = {
      getRandomValues(bytes) {
        bytes.forEach((_, index) => { bytes[index] = index })
        return bytes
      },
    }

    expect(createClientId(cryptoWithoutRandomUUID)).toBe('00010203-0405-4607-8809-0a0b0c0d0e0f')
  })
})
