import { describe, expect, test } from 'vitest'
import { consumeModelToken } from './modelTokenParser'

describe('consumeModelToken', () => {
  test('consumes ordinary voice stream deltas exactly once', () => {
    const state = { raw: '', thought: '', inThinking: false }
    const pieces = ['你好', '！', '作为', 'AI', '助手']

    expect(pieces.map((piece) => consumeModelToken(piece, state))).toEqual(pieces)
    expect(state.raw).toBe('')
  })

  test('keeps split think tags out of the visible answer', () => {
    const state = { raw: '', thought: '', inThinking: false }

    expect(consumeModelToken('<thi', state)).toBe('')
    expect(consumeModelToken('nk>分析</think>答案', state)).toBe('答案')
    expect(state.thought).toBe('分析')
    expect(state.raw).toBe('')
  })
})
