import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import * as THREE from 'three'

import type { ObjectAddPayload } from '@shared/schema/sceneSchema'
import { ObjectFactory, VALID_GEOMETRY_TYPES } from './ObjectFactory'

function buildPayload(overrides: Partial<ObjectAddPayload> = {}): ObjectAddPayload {
  return {
    uuid: 'u1',
    label: 'leaf',
    geometryType: 'SphereGeometry',
    geometryArgs: [0.1, 16, 16],
    material: { type: 'MeshStandardMaterial', color: '#5b3a1a' },
    position: [0, 1, 0],
    stage: 'growth',
    ...overrides,
  }
}

describe('ObjectFactory', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('creates a Mesh with the requested geometry type', () => {
    const mesh = ObjectFactory.create(buildPayload({ geometryType: 'BoxGeometry', geometryArgs: [1, 1, 1] }))
    expect(mesh).toBeInstanceOf(THREE.Mesh)
    expect(mesh.geometry).toBeInstanceOf(THREE.BoxGeometry)
  })

  it('creates a SphereGeometry mesh from sphere payload', () => {
    const mesh = ObjectFactory.create(buildPayload())
    expect(mesh.geometry).toBeInstanceOf(THREE.SphereGeometry)
  })

  it('tags userData.label', () => {
    const mesh = ObjectFactory.create(buildPayload({ label: 'tomato_seed' }))
    expect(mesh.userData.label).toBe('tomato_seed')
  })

  it('tags userData.geometryType', () => {
    const mesh = ObjectFactory.create(buildPayload({ geometryType: 'CylinderGeometry', geometryArgs: [0.5, 0.5, 1, 16] }))
    expect(mesh.userData.geometryType).toBe('CylinderGeometry')
  })

  it('tags userData.geometryArgs', () => {
    const args = [0.5, 0.5, 1, 16]
    const mesh = ObjectFactory.create(buildPayload({ geometryType: 'CylinderGeometry', geometryArgs: args }))
    expect(mesh.userData.geometryArgs).toEqual(args)
  })

  it('tags userData.stage', () => {
    const mesh = ObjectFactory.create(buildPayload({ stage: 'germination' }))
    expect(mesh.userData.stage).toBe('germination')
  })

  it('tags userData.material', () => {
    const material = { type: 'MeshStandardMaterial', color: '#abcdef' }
    const mesh = ObjectFactory.create(buildPayload({ material }))
    expect(mesh.userData.material).toEqual(material)
  })

  it('falls back to BoxGeometry for unknown geometry type', () => {
    const mesh = ObjectFactory.create(buildPayload({ geometryType: 'NotARealGeometry' as string, geometryArgs: [1, 1, 1] }))
    expect(mesh.geometry).toBeInstanceOf(THREE.BoxGeometry)
  })

  it('logs a warning when falling back', () => {
    ObjectFactory.create(buildPayload({ geometryType: 'NotARealGeometry' as string }))
    expect(warnSpy).toHaveBeenCalled()
    const message = warnSpy.mock.calls[0]?.join(' ') ?? ''
    expect(message).toMatch(/NotARealGeometry/i)
  })

  it('falls back to BoxGeometry on constructor failure', () => {
    // Args that THREE rejects (e.g. NaN) should trigger the catch path.
    const mesh = ObjectFactory.create(buildPayload({
      geometryType: 'BoxGeometry',
      geometryArgs: [Number.NaN, Number.NaN, Number.NaN, -1, -1, -1],
    }))
    expect(mesh.geometry).toBeInstanceOf(THREE.BoxGeometry)
  })

  it('sets position from payload', () => {
    const mesh = ObjectFactory.create(buildPayload({ position: [1.5, 2, -3] }))
    expect(mesh.position.x).toBe(1.5)
    expect(mesh.position.y).toBe(2)
    expect(mesh.position.z).toBe(-3)
  })

  it('sets uuid from payload', () => {
    const mesh = ObjectFactory.create(buildPayload({ uuid: 'custom-uuid-123' }))
    expect(mesh.uuid).toBe('custom-uuid-123')
  })

  it('applies optional rotation, scale, and visible when provided', () => {
    const mesh = ObjectFactory.create(buildPayload({
      rotation: [0.1, 0.2, 0.3],
      scale: [2, 2, 2],
      visible: false,
    }))
    expect(mesh.rotation.x).toBeCloseTo(0.1)
    expect(mesh.scale.y).toBe(2)
    expect(mesh.visible).toBe(false)
  })

  it('does not alias caller geometryArgs in userData', () => {
    const args = [0.5, 8, 8]
    const mesh = ObjectFactory.create(buildPayload({ geometryType: 'SphereGeometry', geometryArgs: args }))
    args[0] = 999
    expect((mesh.userData as { geometryArgs: number[] }).geometryArgs).toEqual([0.5, 8, 8])
  })

  it('does not alias caller material in userData', () => {
    const material = { type: 'MeshStandardMaterial', color: '#aaaaaa' }
    const mesh = ObjectFactory.create(buildPayload({ material }))
    material.color = '#zzzzzz'
    expect((mesh.userData as { material: { color: string } }).material.color).toBe('#aaaaaa')
  })

  it('valid geometry types include all seven v1 primitives', () => {
    expect(new Set(VALID_GEOMETRY_TYPES)).toEqual(
      new Set([
        'BoxGeometry',
        'SphereGeometry',
        'CylinderGeometry',
        'ConeGeometry',
        'PlaneGeometry',
        'TorusGeometry',
        'CircleGeometry',
      ]),
    )
  })
})
