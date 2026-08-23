export function createSessionMessageQueue() {
  const tails = new Map()

  function enqueue(sessionId, operation) {
    const previous = tails.get(sessionId) || Promise.resolve()
    const result = previous.then(operation, operation)
    const settled = result.then(() => undefined, () => undefined)
    tails.set(sessionId, settled)
    settled.then(() => {
      if (tails.get(sessionId) === settled) tails.delete(sessionId)
    })
    return result
  }

  function waitFor(sessionId) {
    return tails.get(sessionId) || Promise.resolve()
  }

  return { enqueue, waitFor }
}
