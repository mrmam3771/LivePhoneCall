import { describe, expect, test } from 'vitest'
import { createAutoScrollPolicy } from './autoScrollPolicy'

describe('AI task auto-scroll policy', () => {
  test('stops following the current task after the user scrolls', () => {
    const policy = createAutoScrollPolicy()
    expect(policy.shouldFollow()).toBe(true)

    policy.pause()

    expect(policy.shouldFollow()).toBe(false)
    expect(policy.shouldFollow()).toBe(false)
  })

  test('resumes following when the next AI task starts', () => {
    const policy = createAutoScrollPolicy()
    policy.pause()

    policy.startTask()

    expect(policy.shouldFollow()).toBe(true)
  })
})
