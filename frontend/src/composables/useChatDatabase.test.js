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

  test('creates custom agents and binds new sessions to them', async () => {
    database = useChatDatabase()
    await database.open()

    const agents = await database.listAgents()
    expect(agents).toEqual([
      expect.objectContaining({ id: 'qwen-general', builtIn: true }),
    ])

    const agent = await database.createAgent({
      name: 'Sales assistant',
      description: 'Handles product calls',
      systemPrompt: 'Answer as a concise sales assistant.',
      provider: 'deepseek',
      model: 'deepseek-chat',
      language: 'Chinese',
      voice: 'Vivian',
    })
    const session = await database.createSession(agent.id)

    expect(session.agentId).toBe(agent.id)
    expect(await database.listAgents()).toContainEqual(
      expect.objectContaining({ id: agent.id, name: 'Sales assistant', builtIn: false }),
    )
  })

  test('updates agents and falls sessions back when a custom agent is deleted', async () => {
    database = useChatDatabase()
    await database.open()
    const agent = await database.createAgent({
      name: 'Support',
      description: '',
      systemPrompt: 'Help the customer.',
      provider: 'openai',
      model: 'gpt-5-mini',
      language: 'Auto',
      voice: 'Ryan',
    })
    await database.updateAgent({ ...agent, name: 'Support Pro' })
    const session = await database.createSession(agent.id)

    expect(await database.listAgents()).toContainEqual(
      expect.objectContaining({ id: agent.id, name: 'Support Pro' }),
    )

    await database.deleteAgent(agent.id)
    expect((await database.listSessions()).find((item) => item.id === session.id).agentId).toBe('qwen-general')
    await expect(database.deleteAgent('qwen-general')).rejects.toThrow('built-in')
  })

  test('assigns a different Agent to an existing conversation', async () => {
    database = useChatDatabase()
    await database.open()
    const firstSession = await database.createSession('qwen-general')
    const agent = await database.createAgent({
      name: 'English support',
      description: '',
      systemPrompt: 'Reply in English.',
      provider: 'openai',
      baseUrl: '',
      model: 'gpt-5-mini',
      language: 'English',
      voice: 'Ryan',
    })

    await database.setSessionAgent(firstSession.id, agent.id)

    expect((await database.listSessions()).find((session) => session.id === firstSession.id).agentId).toBe(agent.id)
  })
})
