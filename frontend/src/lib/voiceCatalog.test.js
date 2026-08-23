import { describe, expect, it } from 'vitest'
import { resolveVoiceForText, voiceById } from './voiceCatalog'

describe('voice catalog', () => {
  it('uses native voices for automatic language matching', () => {
    expect(resolveVoiceForText('How can I help you?')).toBe('Aiden')
    expect(resolveVoiceForText('今天有什么可以帮你的吗？')).toBe('Vivian')
    expect(resolveVoiceForText('こんにちは')).toBe('Ono_Anna')
    expect(resolveVoiceForText('안녕하세요')).toBe('Sohee')
  })

  it('honours an explicitly selected voice', () => {
    expect(resolveVoiceForText('Hello', 'Ryan')).toBe('Ryan')
    expect(voiceById('not-a-voice').id).toBe('Auto')
  })
})
