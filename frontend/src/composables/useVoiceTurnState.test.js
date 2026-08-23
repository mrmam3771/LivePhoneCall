import { describe, expect, test } from 'vitest'
import { createVoiceTurnState } from './useVoiceTurnState'

describe('createVoiceTurnState', () => {
  test('allows only one active turn and ignores microphone input until playback ends', () => {
    const voice = createVoiceTurnState()

    expect(voice.shouldCapture()).toBe(true)
    expect(voice.beginTurn()).toBe(true)
    expect(voice.beginTurn()).toBe(false)
    expect(voice.shouldCapture()).toBe(false)

    voice.beginPlayback()
    expect(voice.phase()).toBe('speaking')
    expect(voice.shouldCapture()).toBe(false)

    voice.beginCooldown()
    expect(voice.phase()).toBe('cooldown')
    expect(voice.shouldCapture()).toBe(false)

    voice.finishTurn()
    expect(voice.phase()).toBe('listening')
    expect(voice.shouldCapture()).toBe(true)
  })

  test('stays closed after a call ends', () => {
    const voice = createVoiceTurnState()
    expect(voice.beginTurn()).toBe(true)

    voice.close()
    voice.finishTurn()

    expect(voice.phase()).toBe('closed')
    expect(voice.shouldCapture()).toBe(false)
    expect(voice.beginTurn()).toBe(false)
  })

  test('interrupts an AI response without ending the call', () => {
    const voice = createVoiceTurnState()
    expect(voice.beginTurn()).toBe(true)
    voice.beginPlayback()

    voice.interruptTurn()

    expect(voice.phase()).toBe('listening')
    expect(voice.shouldCapture()).toBe(true)
    expect(voice.beginTurn()).toBe(true)
  })
})
