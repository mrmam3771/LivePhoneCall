export async function streamModelReply({ text, conversationId, history = [], agent, onToken, onThinking, signal, fetchImpl = fetch }) {
  const response = await fetchImpl('/api/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, conversation_id: conversationId, history, agent }),
    signal,
  })
  if (!response.ok || !response.body) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `Model request failed (${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let pending = ''
  let reply = ''
  let thinking = ''

  function consume(block) {
    const kind = block.match(/^event: (.+)$/m)?.[1]
    const raw = block.match(/^data: (.+)$/m)?.[1]
    if (!kind || !raw) return
    const piece = JSON.parse(raw).text || ''
    if (kind === 'token' && piece) {
      reply += piece
      onToken?.(reply, piece)
    }
    if (kind === 'thinking' && piece) {
      thinking += piece
      onThinking?.(thinking, piece)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    pending += decoder.decode(value, { stream: true })
    const blocks = pending.split('\n\n')
    pending = blocks.pop() || ''
    blocks.forEach(consume)
  }
  if (pending.trim()) consume(pending)
  if (!reply.trim()) throw new Error('The language model returned an empty response')
  return reply
}
