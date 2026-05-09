import { describe, expect, it } from 'vitest'
import * as THREE from 'three'

import { ActiveWindow } from '@/serialization/activeWindow'
import { ObjectIndex } from '@/serialization/objectIndex'

import { buildReadablePayload } from './useSceneReadable'

function buildScene(): { scene: THREE.Scene; idx: ObjectIndex; win: ActiveWindow } {
  const scene = new THREE.Scene()
  const idx = new ObjectIndex()
  const win = new ActiveWindow()
  return { scene, idx, win }
}

function makeMesh(uuid: string, label: string): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(1, 1, 1),
    new THREE.MeshStandardMaterial({ color: '#ffffff' }),
  )
  mesh.uuid = uuid
  mesh.userData = { label, geometryType: 'BoxGeometry', geometryArgs: [1, 1, 1] }
  return mesh
}

describe('buildReadablePayload', () => {
  it('contains an activeWindow array', () => {
    const { scene, idx, win } = buildScene()
    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })
    expect(Array.isArray(payload.activeWindow)).toBe(true)
  })

  it('contains a fullIndex map', () => {
    const { scene, idx, win } = buildScene()
    idx.add('u1', 'leaf')
    idx.add('u2', 'stem')

    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })

    expect(payload.fullIndex).toEqual({ u1: 'leaf', u2: 'stem' })
  })

  it('does not contain Float32Array data', () => {
    const { scene, idx, win } = buildScene()
    scene.add(makeMesh('u1', 'a'))
    idx.add('u1', 'a')
    win.push('u1')

    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })
    const json = JSON.stringify(payload)

    expect(json).not.toContain('Float32Array')
    expect(json).not.toContain('"attributes"')
  })

  it('contains spatialSummary with four zones', () => {
    const { scene, idx, win } = buildScene()
    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })
    expect(Object.keys(payload.spatialSummary).sort()).toEqual([
      'ground',
      'lower',
      'mid',
      'upper',
    ])
  })

  it('emits objectCount equal to non-root traversal count', () => {
    const { scene, idx, win } = buildScene()
    scene.add(makeMesh('u1', 'a'))
    scene.add(makeMesh('u2', 'b'))
    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })
    expect(payload.objectCount).toBe(2)
  })

  it('returns a payload that is plain-JSON serializable', () => {
    const { scene, idx, win } = buildScene()
    scene.add(makeMesh('u1', 'a'))
    idx.add('u1', 'a')
    win.push('u1')

    const payload = buildReadablePayload(scene, { objectIndex: idx, activeWindow: win })

    expect(() => JSON.parse(JSON.stringify(payload))).not.toThrow()
  })
})
