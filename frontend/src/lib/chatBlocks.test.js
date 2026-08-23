import { describe, expect, test } from 'vitest'
import { buildChatBlocks } from './chatBlocks'

const message = (id, role, type, content) => ({ id, role, type, content, createdAt: Number(id) || 1 })

describe('buildChatBlocks', () => {
  test('puts thinking and the final answer in one assistant block', () => {
    const blocks = buildChatBlocks([
      message('1', 'user', 'text', 'Hello'),
      message('2', 'assistant', 'thinking', 'Working it out'),
      message('3', 'assistant', 'text', 'Hi there'),
    ])

    expect(blocks).toHaveLength(2)
    expect(blocks[1]).toMatchObject({
      role: 'assistant',
      thinking: { content: 'Working it out' },
      message: { content: 'Hi there' },
    })
  })

  test('does not merge assistant messages across a user turn', () => {
    const blocks = buildChatBlocks([
      message('1', 'assistant', 'thinking', 'First thought'),
      message('2', 'user', 'text', 'Next question'),
      message('3', 'assistant', 'text', 'Second answer'),
    ])

    expect(blocks).toHaveLength(3)
  })

  test('attaches the pending indicator to the current assistant block', () => {
    const blocks = buildChatBlocks([
      message('1', 'user', 'text', 'Hello'),
      message('2', 'assistant', 'thinking', 'Still thinking'),
    ], true)

    expect(blocks).toHaveLength(2)
    expect(blocks[1]).toMatchObject({ role: 'assistant', pending: true })
  })

  test('merges late thinking into an answer that was stored first', () => {
    const blocks = buildChatBlocks([
      message('1', 'user', 'text', 'Hello'),
      message('2', 'assistant', 'text', 'Final answer'),
      message('3', 'assistant', 'thinking', 'Late thought'),
    ])

    expect(blocks).toHaveLength(2)
    expect(blocks[1]).toMatchObject({
      role: 'assistant',
      thinking: { content: 'Late thought' },
      message: { content: 'Final answer' },
    })
  })
})
