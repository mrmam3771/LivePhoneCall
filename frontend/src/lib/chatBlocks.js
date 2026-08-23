export function buildChatBlocks(messages, pending = false) {
  const blocks = []

  for (const message of messages) {
    if (message.role !== 'assistant') {
      blocks.push({ id: `message-${message.id}`, role: message.role, message, thinking: null, pending: false })
      continue
    }

    const previous = blocks.at(-1)
    if (message.type === 'thinking') {
      if (previous?.role === 'assistant' && previous.message && !previous.thinking) {
        previous.thinking = message
        previous.id = `${previous.id}-${message.id}`
      } else {
        blocks.push({ id: `assistant-${message.id}`, role: 'assistant', message: null, thinking: message, pending: false })
      }
    } else if (previous?.role === 'assistant' && previous.thinking && !previous.message) {
      previous.message = message
      previous.id = `${previous.id}-${message.id}`
    } else {
      blocks.push({ id: `assistant-${message.id}`, role: 'assistant', message, thinking: null, pending: false })
    }
  }

  if (pending) {
    const previous = blocks.at(-1)
    if (previous?.role === 'assistant') previous.pending = true
    else blocks.push({ id: 'assistant-pending', role: 'assistant', message: null, thinking: null, pending: true })
  }

  return blocks
}
