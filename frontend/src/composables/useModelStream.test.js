import { describe, expect, test, vi } from 'vitest'
import { streamModelReply } from './useModelStream'

describe('streamModelReply', () => {
  test('sends the selected Provider and parses streamed assistant tokens', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      'event: token\ndata: {"text":"Hello"}\n\nevent: token\ndata: {"text":" world"}\n\nevent: done\ndata: {}\n\n',
      { status: 200 },
    ))
    const updates = []

    const reply = await streamModelReply({
      text: 'Hi', conversationId: 'session-1', history: [], agent: { model: 'deepseek-chat' },
      onToken: (text) => updates.push(text), fetchImpl: fetchMock,
    })

    expect(fetchMock).toHaveBeenCalledWith('/api/agent/stream', expect.objectContaining({ method: 'POST' }))
    expect(reply).toBe('Hello world')
    expect(updates).toEqual(['Hello', 'Hello world'])
  })

  test('forwards cancellation to the active model request', async () => {
    const controller = new AbortController()
    const fetchMock = vi.fn((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new DOMException('Stopped', 'AbortError')))
    }))

    const request = streamModelReply({
      text: 'Stop me',
      conversationId: 'session-1',
      agent: { model: 'deepseek-chat' },
      signal: controller.signal,
      fetchImpl: fetchMock,
    })
    controller.abort()

    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
  })
})
