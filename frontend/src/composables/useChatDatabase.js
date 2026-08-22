const DATABASE_NAME = 'qwen-voice-agent'
const DATABASE_VERSION = 2

function makeId() {
  return crypto.randomUUID?.() || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

function transactionDone(transaction) {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = resolve
    transaction.onerror = () => reject(transaction.error)
    transaction.onabort = () => reject(transaction.error)
  })
}

export function useChatDatabase() {
  let database

  async function open() {
    if (database) return database
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains('sessions')) {
        const sessions = db.createObjectStore('sessions', { keyPath: 'id' })
        sessions.createIndex('updatedAt', 'updatedAt')
      }
      if (!db.objectStoreNames.contains('messages')) {
        const messages = db.createObjectStore('messages', { keyPath: 'id' })
        messages.createIndex('sessionId', 'sessionId')
      }
    }
    database = await requestResult(request)
    return database
  }

  async function listSessions() {
    const items = await requestResult(database.transaction('sessions').objectStore('sessions').getAll())
    return items.sort((a, b) => b.updatedAt - a.updatedAt)
  }

  async function createSession() {
    const now = Date.now()
    const session = { id: makeId(), title: 'New conversation / 新会话', preview: 'No messages yet / 暂无消息', createdAt: now, updatedAt: now }
    const transaction = database.transaction('sessions', 'readwrite')
    transaction.objectStore('sessions').add(session)
    await transactionDone(transaction)
    return session
  }

  async function listMessages(sessionId) {
    const store = database.transaction('messages').objectStore('messages')
    const items = await requestResult(store.index('sessionId').getAll(IDBKeyRange.only(sessionId)))
    return items.sort((a, b) => a.createdAt - b.createdAt)
  }

  async function addMessage(sessionId, payload) {
    const now = Date.now()
    const message = { id: makeId(), sessionId, createdAt: now, ...payload }
    const transaction = database.transaction(['sessions', 'messages'], 'readwrite')
    const sessionStore = transaction.objectStore('sessions')
    const session = await requestResult(sessionStore.get(sessionId))
    transaction.objectStore('messages').add(message)
    if (session) {
      const summary = payload.type === 'audio' ? `Voice note · ${formatDuration(payload.duration)}` : payload.content.replace(/\s+/g, ' ').trim()
      if (session.title === 'New conversation / 新会话') session.title = payload.type === 'audio' ? 'Voice conversation / 语音会话' : summary.slice(0, 34)
      session.preview = summary.slice(0, 62)
      session.updatedAt = now
      sessionStore.put(session)
    }
    await transactionDone(transaction)
    return message
  }

  async function deleteSession(sessionId) {
    const transaction = database.transaction(['sessions', 'messages'], 'readwrite')
    transaction.objectStore('sessions').delete(sessionId)
    const cursorRequest = transaction.objectStore('messages').index('sessionId').openCursor(IDBKeyRange.only(sessionId))
    cursorRequest.onsuccess = (event) => {
      const cursor = event.target.result
      if (!cursor) return
      cursor.delete()
      cursor.continue()
    }
    await transactionDone(transaction)
  }

  function close() {
    database?.close()
    database = undefined
  }

  return { open, close, listSessions, createSession, listMessages, addMessage, deleteSession }
}

export function formatDuration(seconds = 0) {
  const value = Math.max(0, Math.round(seconds))
  return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`
}
