import { ref } from 'vue'

export function usePendingReplies() {
  const replyCounts = ref(new Map())

  function start(sessionId) {
    const next = new Map(replyCounts.value)
    next.set(sessionId, (next.get(sessionId) || 0) + 1)
    replyCounts.value = next
  }

  function finish(sessionId) {
    const next = new Map(replyCounts.value)
    const remaining = (next.get(sessionId) || 0) - 1
    if (remaining > 0) next.set(sessionId, remaining)
    else next.delete(sessionId)
    replyCounts.value = next
  }

  return {
    start,
    finish,
    has: (sessionId) => replyCounts.value.has(sessionId),
  }
}
