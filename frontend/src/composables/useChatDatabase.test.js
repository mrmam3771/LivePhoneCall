import 'fake-indexeddb/auto'
import { afterEach, beforeEach, describe, expect, test } from 'vitest'
import { useChatDatabase } from './useChatDatabase'

function deleteDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase('qwen-voice-agent')
    request.onsuccess = resolve
    request.onerror = () => reject(request.error)
    request.onblocked = resolve
  })
}

describe('useChatDatabase', () => {
  let database

  beforeEach(deleteDatabase)
  afterEach(() => database?.close())

  test('persists sessions and text messages', async () => {
    database = useChatDatabase()
    await database.open()
    const session = await database.createSession()
    await database.addMessage(session.id, {
      role: 'user',
      type: 'text',
      content: 'A persistent message',
    })

    const sessions = await database.listSessions()
    const messages = await database.listMessages(session.id)

    expect(sessions[0]).toMatchObject({
      id: session.id,
      title: 'A persistent message',
      preview: 'A persistent message',
    })
    expect(messages).toHaveLength(1)
    expect(messages[0]).toMatchObject({ role: 'user', content: 'A persistent message' })
  })

  test('stores audio blobs and removes all messages with their session', async () => {
    database = useChatDatabase()
    await database.open()
    const session = await database.createSession()
    const audio = new Blob(['voice'], { type: 'audio/webm' })
    await database.addMessage(session.id, {
      role: 'user',
      type: 'audio',
      content: 'Voice note / 语音留言',
      audio,
      duration: 7,
    })

    expect(await database.listMessages(session.id)).toEqual([
      expect.objectContaining({ type: 'audio', duration: 7, audio }),
    ])

    await database.deleteSession(session.id)
    expect(await database.listSessions()).toEqual([])
    expect(await database.listMessages(session.id)).toEqual([])
  })
})
