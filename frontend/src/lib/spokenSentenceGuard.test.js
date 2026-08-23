import { describe, expect, test } from 'vitest'
import { createSpokenSentenceGuard } from './spokenSentenceGuard'

describe('spoken sentence guard', () => {
  test('rejects a repeated meaningful sentence', () => {
    const guard = createSpokenSentenceGuard()

    expect(guard.accept('I can help you with that.')).toBe(true)
    expect(guard.accept(' I can   help you with that. ')).toBe(false)
  })

  test('allows distinct sentences and short acknowledgements', () => {
    const guard = createSpokenSentenceGuard()

    expect(guard.accept('First useful sentence.')).toBe(true)
    expect(guard.accept('Second useful sentence.')).toBe(true)
    expect(guard.accept('OK.')).toBe(true)
    expect(guard.accept('OK.')).toBe(true)
  })
})
