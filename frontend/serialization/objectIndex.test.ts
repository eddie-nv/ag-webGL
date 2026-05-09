import { describe, expect, it } from 'vitest'
import { ObjectIndex } from './objectIndex'

describe('ObjectIndex', () => {
  it('add and getAll returns correct map', () => {
    const idx = new ObjectIndex()
    idx.add('u1', 'leaf')
    idx.add('u2', 'stem')

    expect(idx.getAll()).toEqual({ u1: 'leaf', u2: 'stem' })
  })

  it('size increments on each add', () => {
    const idx = new ObjectIndex()
    expect(idx.size()).toBe(0)
    idx.add('u1', 'leaf')
    expect(idx.size()).toBe(1)
    idx.add('u2', 'stem')
    expect(idx.size()).toBe(2)
  })

  it('getAll returns a copy, not the internal map', () => {
    const idx = new ObjectIndex()
    idx.add('u1', 'leaf')

    const snapshot = idx.getAll()
    snapshot.u1 = 'mutated'

    expect(idx.getAll()).toEqual({ u1: 'leaf' })
  })

  it('add overwrites existing label for the same uuid', () => {
    const idx = new ObjectIndex()
    idx.add('u1', 'leaf')
    idx.add('u1', 'leafy')

    expect(idx.getAll()).toEqual({ u1: 'leafy' })
    expect(idx.size()).toBe(1)
  })
})
