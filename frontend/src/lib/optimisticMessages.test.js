import { describe, expect, test } from 'vitest'
import { conversationTitle, removeMessage, replaceMessage } from './optimisticMessages'

describe('optimistic messages', () => {
  test('replaces a temporary message in place without rebuilding the list', () => {
    const before = [
      { id: 'old', content: 'Earlier' },
      { id: 'temp-user', content: 'Hello' },
      { id: 'pending', type: 'status' },
    ]
    const saved = { id: 'stored-user', content: 'Hello' }

    const after = replaceMessage(before, 'temp-user', saved)

    expect(after).toEqual([before[0], saved, before[2]])
  })

  test('removes a failed optimistic message only', () => {
    const before = [{ id: 'old' }, { id: 'temp-user' }]
    expect(removeMessage(before, 'temp-user')).toEqual([before[0]])
  })

  test('creates a concise ChatGPT-style title without exposing identifiers', () => {
    expect(conversationTitle('  你好  ')).toBe('Greeting / 问候')
    expect(conversationTitle('请帮我排查语音电话重复输出的问题，并给出解决方式')).toBe('请帮我排查语音电话重复输出的问题，并给出解决方式')
  })
})
