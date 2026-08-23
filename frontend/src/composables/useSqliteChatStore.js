import { DEFAULT_AGENT_ID, useChatDatabase } from './useChatDatabase'

const MIGRATION_KEY = 'qwen-chat-sqlite-migration-v1'

async function request(path, options = {}) {
  const response = await fetch(`/api/chat${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (response.status === 204) return undefined
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || body.error || `Chat storage request failed (${response.status})`)
  return body
}

async function requestModelCatalog(refresh = false) {
  const response = await fetch(`/api/catalog/models${refresh ? '?refresh=true' : ''}`)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Model catalog request failed (${response.status})`)
  return body
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
        for (const message of messages.filter((item) => item.type !== 'audio')) {
          await request(`/sessions/${created.id}/messages`, {
            method: 'POST',
            body: JSON.stringify(message),
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
    if (payload.type === 'audio') throw new Error('Audio recordings are not stored in live call mode')
    return request(`/sessions/${sessionId}/messages`, { method: 'POST', body: JSON.stringify(payload) })
  }

  return {
    open,
    listSessions: () => request('/sessions'),
    createSession: (agentId = DEFAULT_AGENT_ID, modelId) => request('/sessions', { method: 'POST', body: JSON.stringify({ agentId, modelId }) }),
    listMessages: (sessionId) => request(`/sessions/${sessionId}/messages`),
    addMessage,
    deleteSession: (sessionId) => request(`/sessions/${sessionId}`, { method: 'DELETE' }),
    setSessionAgent: (sessionId, agentId) => request(`/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify({ agentId }) }),
    setSessionModel: (sessionId, modelId) => request(`/sessions/${sessionId}`, { method: 'PATCH', body: JSON.stringify({ modelId }) }),
    listAgents: () => request('/agents'),
    createAgent: (agent) => request('/agents', { method: 'POST', body: JSON.stringify(agent) }),
    updateAgent: (agent) => request(`/agents/${agent.id}`, { method: 'PUT', body: JSON.stringify(agent) }),
    deleteAgent: (agentId) => request(`/agents/${agentId}`, { method: 'DELETE' }),
    listProviders: () => request('/providers'),
    createProvider: (provider) => request('/providers', { method: 'POST', body: JSON.stringify(provider) }),
    updateProvider: (provider) => request(`/providers/${provider.id}`, { method: 'PUT', body: JSON.stringify(provider) }),
    deleteProvider: (providerId) => request(`/providers/${providerId}`, { method: 'DELETE' }),
    listModels: () => request('/models'),
    createModel: (model) => request('/models', { method: 'POST', body: JSON.stringify(model) }),
    updateModel: (model) => request(`/models/${model.id}`, { method: 'PUT', body: JSON.stringify(model) }),
    deleteModel: (modelId) => request(`/models/${modelId}`, { method: 'DELETE' }),
    getModelCatalog: requestModelCatalog,
  }
}

export { DEFAULT_AGENT_ID }

export function formatDuration(seconds = 0) {
  const value = Math.max(0, Math.round(seconds))
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}
