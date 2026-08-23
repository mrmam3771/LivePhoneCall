export function createVoiceTurnState() {
  let current = 'listening'

  return {
    phase: () => current,
    shouldCapture: () => current === 'listening',
    beginTurn() {
      if (current !== 'listening') return false
      current = 'processing'
      return true
    },
    beginPlayback() {
      if (current !== 'closed') current = 'speaking'
    },
    beginCooldown() {
      if (current !== 'closed') current = 'cooldown'
    },
    interruptTurn() {
      if (current !== 'closed') current = 'listening'
    },
    finishTurn() {
      if (current !== 'closed') current = 'listening'
    },
    close() {
      current = 'closed'
    },
  }
}
