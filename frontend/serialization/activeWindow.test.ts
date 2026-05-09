import { describe, expect, it } from 'vitest'
import { ACTIVE_WINDOW_CAPACITY, ActiveWindow } from './activeWindow'

describe('ActiveWindow', () => {
  it('capacity is capped at 3', () => {
    expect(ACTIVE_WINDOW_CAPACITY).toBe(3)
  })

  it('push drops oldest when at capacity', () => {
    const win = new ActiveWindow()
    win.push('u1')
    win.push('u2')
    win.push('u3')
    win.push('u4')

    expect(win.toArray()).toEqual(['u2', 'u3', 'u4'])
  })

  it('contains returns true only for uuids currently in the window', () => {
    const win = new ActiveWindow()
    win.push('u1')
    win.push('u2')
    win.push('u3')

    expect(win.contains('u2')).toBe(true)
    expect(win.contains('ghost')).toBe(false)

    win.push('u4')
    expect(win.contains('u1')).toBe(false)
    expect(win.contains('u4')).toBe(true)
  })

  it('toArray returns the entries in insertion order (oldest first)', () => {
    const win = new ActiveWindow()
    win.push('u1')
    win.push('u2')
    expect(win.toArray()).toEqual(['u1', 'u2'])
  })

  it('pushing the same uuid again moves it to the most-recent slot', () => {
    const win = new ActiveWindow()
    win.push('u1')
    win.push('u2')
    win.push('u1')

    expect(win.toArray()).toEqual(['u2', 'u1'])
  })
})
