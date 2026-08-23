import { describe, expect, test } from 'vitest'
import { createSessionMessageQueue } from './sessionMessageQueue'

describe('session message queue', () => {
  test('commits adjacent voice-turn messages in enqueue order', async () => {
    const queue = createSessionMessageQueue()
    const committed = []
    let releaseFirst
    const firstGate = new Promise((resolve) => { releaseFirst = resolve })

    const first = queue.enqueue('session-1', async () => {
      await firstGate
      committed.push('first assistant reply')
    })
    const second = queue.enqueue('session-1', async () => {
      committed.push('second user message')
    })

    await Promise.resolve()
    expect(committed).toEqual([])
    releaseFirst()
    await Promise.all([first, second])

    expect(committed).toEqual(['first assistant reply', 'second user message'])
  })

  test('keeps different conversations independent', async () => {
    const queue = createSessionMessageQueue()
    let releaseFirst
    const firstGate = new Promise((resolve) => { releaseFirst = resolve })
    const committed = []

    const slow = queue.enqueue('session-1', () => firstGate.then(() => committed.push('one')))
    await queue.enqueue('session-2', async () => { committed.push('two') })
    expect(committed).toEqual(['two'])
    releaseFirst()
    await slow
  })
})
