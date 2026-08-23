import { describe, expect, test } from 'vitest'
import { usePendingReplies } from './usePendingReplies'

describe('usePendingReplies', () => {
  test('tracks waiting state independently for each conversation', () => {
    const pending = usePendingReplies()

    pending.start('session-a')
    pending.start('session-b')
    expect(pending.has('session-a')).toBe(true)
    expect(pending.has('session-b')).toBe(true)

    pending.finish('session-a')
    expect(pending.has('session-a')).toBe(false)
    expect(pending.has('session-b')).toBe(true)
  })

  test('stays pending until every reply in the same conversation finishes', () => {
    const pending = usePendingReplies()

    pending.start('session-a')
    pending.start('session-a')
    pending.finish('session-a')
    expect(pending.has('session-a')).toBe(true)

    pending.finish('session-a')
    expect(pending.has('session-a')).toBe(false)
  })
})
