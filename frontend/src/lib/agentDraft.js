export function canSaveAgent(draft) {
  return Boolean(draft.name?.trim())
}

export function normaliseAgentDraft(draft) {
  return {
    ...draft,
    name: draft.name?.trim() || '',
    description: draft.description?.trim() || '',
    systemPrompt: draft.systemPrompt?.trim() || '',
  }
}
