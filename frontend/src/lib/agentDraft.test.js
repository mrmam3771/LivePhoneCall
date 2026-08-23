import { describe, expect, test } from 'vitest'
import { canSaveAgent, normaliseAgentDraft } from './agentDraft'

describe('Agent draft', () => {
  test('allows an Agent without optional system instructions', () => {
    const draft = {
      id: '',
      name: '  Phone assistant  ',
      description: '  Answers calls  ',
      systemPrompt: '   ',
      language: 'Auto',
      voice: 'Vivian',
      builtIn: false,
    }

    expect(canSaveAgent(draft)).toBe(true)
    expect(normaliseAgentDraft(draft)).toEqual({
      ...draft,
      name: 'Phone assistant',
      description: 'Answers calls',
      systemPrompt: '',
    })
  })

  test('still requires a non-empty Agent name', () => {
    expect(canSaveAgent({ name: '   ', systemPrompt: '' })).toBe(false)
  })
})
