import { DEFAULT_AGENT_ID, useChatDatabase } from './useChatDatabase'

const MIGRATION_KEY = 'qwen-chat-sqlite-migration-v1'

async function request(path, options = {}) {
  const response = await fetch(`/api/chat${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (response.status === 204) return undefined
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Chat storage request failed (${response.status})`)
  return body
}

function blobToBase64(blob) {
  if (!blob) return Promise.resolve(undefined)
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(blob)
  })
}

function base64ToBlob(value, mimeType) {
  if (!value) return undefined
  const bytes = atob(value)
  const data = new Uint8Array(bytes.length)
  for (let index = 0; index < bytes.length; index += 1) data[index] = bytes.charCodeAt(index)
  return new Blob([data], { type: mimeType || 'audio/webm' })
}

function mapMessage(message) {
  const { audioBase64, ...rest } = message
  return audioBase64 ? { ...rest, audio: base64ToBlob(audioBase64, message.mimeType) } : rest
}

export function useSqliteChatStore() {
  async function migrateIndexedDbIfNeeded(bootstrap) {
    if (bootstrap.sessions.length || localStorage.getItem(MIGRATION_KEY)) return
    const legacy = useChatDatabase()
    try {
      await legacy.open()
      const [agents, sessions] = await Promise.all([legacy.listAgents(), legacy.listSessions()])
      const agentIds = new Map([[DEFAULT_AGENT_ID, DEFAULT_AGENT_ID]])
      for (const agent of agents.filter((item) => !item.builtIn)) {
        const created = await request('/agents', { method: 'POST', body: JSON.stringify(agent) })
        agentIds.set(agent.id, created.id)
      }
      for (const session of sessions) {
        const created = await request('/sessions', { method: 'POST', body: JSON.stringify({ agentId: agentIds.get(session.agentId) || DEFAULT_AGENT_ID }) })
        const messages = await legacy.listMessages(session.id)
        for (const message of messages) {
          await request(`/sessions/${created.id}/messages`, {
            method: 'POST',
            body: JSON.stringify({ ...message, audioBase64: await blobToBase64(message.audio) }),
          })
        }
      }
    } finally {
      legacy.close()
      localStorage.setItem(MIGRATION_KEY, 'done')
    }
  }

  async function open() {
    let bootstrap = await request('/bootstrap')
    await migrateIndexedDbIfNeeded(bootstrap)
    bootstrap = await request('/bootstrap')
    return bootstrap
  }

  async function addMessage(sessionId, payload) {
    const audioBase64 = await blobToBase64(payload.audio)
    return mapMessage(await request(`/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify({ ...payload, audioBase64 }) }))
  }

  return {
    open,
    listSessions: () => request('/sessions'),
    createSession: (agentId = DEFAULT_AGENT_ID) => request('/sessions', { method: 'POST', body: JSON.stringify({ agentId }) }),
    listMessages: async (sessionId) => (await request(`/sessions/${sessionId}/messages`)).map(mapMessage),
    addMessage,
    deleteSession: (sessionId) => request(`/sessions/${sessionId}`, { method: 'DELETE' }),
    setSessionAgent: (sessionId, agentId) => request(`/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify({ agentId }) }),
    listAgents: () => request('/agents'),
    createAgent: (agent) => request('/agents', { method: 'POST', body: JSON.stringify(agent) }),
    updateAgent: (agent) => request(`/agents/${agent.id}`, { method: 'PUT', body: JSON.stringify(agent) }),
    deleteAgent: (agentId) => request(`/agents/${agentId}`, { method: 'DELETE' }),
  }
}

export { DEFAULT_AGENT_ID }

export function formatDuration(seconds = 0) {
  const value = Math.max(0, Math.round(seconds))
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}
