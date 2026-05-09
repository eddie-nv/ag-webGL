import { describe, expect, it, vi } from 'vitest'
import * as THREE from 'three'

import { ActiveWindow } from './activeWindow'
import { ObjectIndex } from './objectIndex'
import { serializeScene } from './sceneSerializer'

interface MeshOpts {
  uuid?: string
  label?: string
  stage?: string
  geometryType?: string
  geometryArgs?: number[]
  position?: [number, number, number]
  materialColor?: string
}

function makeMesh(opts: MeshOpts = {}): THREE.Mesh {
  const geometry = new THREE.BoxGeometry(1, 1, 1)
  const material = new THREE.MeshStandardMaterial({ color: opts.materialColor ?? '#ffffff' })
  const mesh = new THREE.Mesh(geometry, material)
  if (opts.uuid) mesh.uuid = opts.uuid
  if (opts.position) mesh.position.set(...opts.position)
  mesh.userData = {
    label: opts.label ?? 'box',
    stage: opts.stage ?? 'default',
    geometryType: opts.geometryType ?? 'BoxGeometry',
    geometryArgs: opts.geometryArgs ?? [1, 1, 1],
    material: { type: 'MeshStandardMaterial', color: opts.materialColor ?? '#ffffff' },
  }
  return mesh
}

function buildContext(): { idx: ObjectIndex; win: ActiveWindow } {
  return { idx: new ObjectIndex(), win: new ActiveWindow() }
}

describe('serializeScene', () => {
  it('handles an empty scene without throwing', () => {
    const scene = new THREE.Scene()
    const { idx, win } = buildContext()

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(result.activeWindow).toEqual([])
    expect(result.fullIndex).toEqual({})
    expect(result.objectCount).toBe(0)
  })

  it('objectCount matches non-root traversal count', () => {
    const scene = new THREE.Scene()
    scene.add(makeMesh({ uuid: 'u1' }))
    scene.add(makeMesh({ uuid: 'u2' }))
    scene.add(makeMesh({ uuid: 'u3' }))
    const { idx, win } = buildContext()

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(result.objectCount).toBe(3)
  })

  it('serializes object into activeWindow when uuid is in window', () => {
    const scene = new THREE.Scene()
    const mesh = makeMesh({ uuid: 'u1', label: 'leaf', position: [0, 1, 0] })
    scene.add(mesh)

    const { idx, win } = buildContext()
    idx.add('u1', 'leaf')
    win.push('u1')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(result.activeWindow).toHaveLength(1)
    expect(result.activeWindow[0].uuid).toBe('u1')
    expect(result.activeWindow[0].label).toBe('leaf')
    expect(result.activeWindow[0].position).toEqual([0, 1, 0])
  })

  it('objects not in activeWindow appear in fullIndex only', () => {
    const scene = new THREE.Scene()
    const meshes = [
      makeMesh({ uuid: 'u1', label: 'a' }),
      makeMesh({ uuid: 'u2', label: 'b' }),
      makeMesh({ uuid: 'u3', label: 'c' }),
      makeMesh({ uuid: 'u4', label: 'd' }),
      makeMesh({ uuid: 'u5', label: 'e' }),
    ]
    for (const m of meshes) scene.add(m)

    const { idx, win } = buildContext()
    for (const m of meshes) idx.add(m.uuid, (m.userData as { label: string }).label)
    win.push('u4')
    win.push('u5')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(result.activeWindow).toHaveLength(2)
    expect(Object.keys(result.fullIndex)).toHaveLength(5)
    expect(result.fullIndex).toEqual({ u1: 'a', u2: 'b', u3: 'c', u4: 'd', u5: 'e' })
  })

  it('extracts position, rotation, scale as plain arrays', () => {
    const scene = new THREE.Scene()
    const mesh = makeMesh({ uuid: 'u1' })
    mesh.position.set(1, 2, 3)
    mesh.rotation.set(0.1, 0.2, 0.3)
    mesh.scale.set(2, 2, 2)
    scene.add(mesh)

    const { idx, win } = buildContext()
    idx.add('u1', 'box')
    win.push('u1')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })
    const obj = result.activeWindow[0]

    expect(obj.position).toEqual([1, 2, 3])
    expect(obj.rotation[0]).toBeCloseTo(0.1)
    expect(obj.rotation[1]).toBeCloseTo(0.2)
    expect(obj.rotation[2]).toBeCloseTo(0.3)
    expect(obj.scale).toEqual([2, 2, 2])
    expect(Array.isArray(obj.position)).toBe(true)
    expect(Array.isArray(obj.rotation)).toBe(true)
    expect(Array.isArray(obj.scale)).toBe(true)
  })

  it('does not include geometry.attributes anywhere in the output', () => {
    const scene = new THREE.Scene()
    scene.add(makeMesh({ uuid: 'u1' }))
    const { idx, win } = buildContext()
    idx.add('u1', 'box')
    win.push('u1')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })
    const json = JSON.stringify(result)

    expect(json).not.toContain('attributes')
    expect(json).not.toContain('Float32Array')
    expect(json).not.toContain('"array"')
  })

  it('never calls toJSON on the scene or any object', () => {
    const scene = new THREE.Scene()
    const mesh = makeMesh({ uuid: 'u1' })
    scene.add(mesh)

    const sceneSpy = vi.spyOn(scene, 'toJSON')
    const meshSpy = vi.spyOn(mesh, 'toJSON')
    const geomSpy = vi.spyOn(mesh.geometry, 'toJSON')

    const { idx, win } = buildContext()
    idx.add('u1', 'box')
    win.push('u1')
    serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(sceneSpy).not.toHaveBeenCalled()
    expect(meshSpy).not.toHaveBeenCalled()
    expect(geomSpy).not.toHaveBeenCalled()
  })

  it('flags hasTexture:true on materials with a map, never embeds data', () => {
    const scene = new THREE.Scene()
    const mesh = makeMesh({ uuid: 'u1' })
    const mat = mesh.material as THREE.MeshStandardMaterial
    mat.map = new THREE.Texture()
    scene.add(mesh)

    const { idx, win } = buildContext()
    idx.add('u1', 'box')
    win.push('u1')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })
    const obj = result.activeWindow[0]

    expect(obj.material.hasTexture).toBe(true)
    const json = JSON.stringify(result)
    // The texture object itself must never appear in the payload — only the flag.
    expect(json).not.toContain('"map":')
    expect(json).not.toContain('"image":')
    expect(json).not.toContain('"mapping":')
  })

  it('flags hasTexture:false when the material has no map', () => {
    const scene = new THREE.Scene()
    scene.add(makeMesh({ uuid: 'u1' }))
    const { idx, win } = buildContext()
    idx.add('u1', 'box')
    win.push('u1')

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(result.activeWindow[0].material.hasTexture).toBe(false)
  })

  it('exposes the spatial summary with four zones', () => {
    const scene = new THREE.Scene()
    const { idx, win } = buildContext()

    const result = serializeScene(scene, { objectIndex: idx, activeWindow: win })

    expect(Object.keys(result.spatialSummary).sort()).toEqual([
      'ground',
      'lower',
      'mid',
      'upper',
    ])
  })
})
