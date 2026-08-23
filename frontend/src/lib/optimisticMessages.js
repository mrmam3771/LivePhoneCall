export function replaceMessage(messages, messageId, savedMessage) {
  return messages.map((message) => message.id === messageId ? savedMessage : message)
}

export function removeMessage(messages, messageId) {
  return messages.filter((message) => message.id !== messageId)
}

export function conversationTitle(content) {
  const summary = content.replace(/\s+/g, ' ').trim()
  const greeting = summary.toLocaleLowerCase().replace(/[!！。?.？]+$/g, '')
  if (['hi', 'hello', 'hey', '你好', '您好', '在吗'].includes(greeting)) return 'Greeting / 问候'
  return summary.slice(0, 34) || 'New conversation / 新会话'
}
