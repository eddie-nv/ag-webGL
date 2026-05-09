import { describe, expect, it, vi } from 'vitest'
import * as THREE from 'three'

import type {
  AnimationStartPayload,
  AnimationStopPayload,
  CameraMovePayload,
  LightAddPayload,
  ObjectAddPayload,
  ObjectUpdatePayload,
} from '@shared/schema/sceneSchema'
import { ObjectIndex } from '@/serialization/objectIndex'
import { ActiveWindow } from '@/serialization/activeWindow'
import { SceneController, type AnimationLoopLike } from './SceneController'

function buildAddPayload(overrides: Partial<ObjectAddPayload> = {}): ObjectAddPayload {
  return {
    uuid: 'u1',
    label: 'leaf',
    geometryType: 'BoxGeometry',
    geometryArgs: [1, 1, 1],
    material: { type: 'MeshStandardMaterial', color: '#5b3a1a' },
    position: [0, 1, 0],
    stage: 'growth',
    ...overrides,
  }
}

function buildLightPayload(overrides: Partial<LightAddPayload> = {}): LightAddPayload {
  return {
    uuid: 'l1',
    lightType: 'DirectionalLight',
    color: '#ffffff',
    intensity: 1.0,
    ...overrides,
  }
}

function buildController(animationLoop?: AnimationLoopLike) {
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100)
  const objectIndex = new ObjectIndex()
  const activeWindow = new ActiveWindow()
  const ctrl = new SceneController({
    scene,
    camera,
    objectIndex,
    activeWindow,
    animationLoop,
  })
  return { scene, camera, objectIndex, activeWindow, ctrl }
}

describe('SceneController.addObject', () => {
  it('adds the mesh to the scene', () => {
    const { scene, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    expect(scene.getObjectByProperty('uuid', 'u1')).toBeDefined()
  })

  it('pushes the uuid to the activeWindow', () => {
    const { activeWindow, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    expect(activeWindow.contains('u1')).toBe(true)
  })

  it('registers the label in objectIndex', () => {
    const { objectIndex, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1', label: 'tomato_seed' }))
    expect(objectIndex.getAll()).toEqual({ u1: 'tomato_seed' })
  })
})

describe('SceneController.updateObject', () => {
  it('changes position when given new position', () => {
    const { scene, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1', position: [0, 0, 0] }))
    ctrl.updateObject('u1', { position: [3, 4, 5] })
    const mesh = scene.getObjectByProperty('uuid', 'u1') as THREE.Mesh
    expect(mesh.position.x).toBe(3)
    expect(mesh.position.y).toBe(4)
    expect(mesh.position.z).toBe(5)
  })

  it('pushes the uuid to the activeWindow', () => {
    const { activeWindow, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    activeWindow.push('other')
    activeWindow.push('another')
    activeWindow.push('athird')
    // u1 has been bumped out by the noise above; updateObject must re-add it.
    expect(activeWindow.contains('u1')).toBe(false)
    ctrl.updateObject('u1', { position: [1, 2, 3] })
    expect(activeWindow.contains('u1')).toBe(true)
  })

  it('is a no-op when the uuid is unknown', () => {
    const { scene, ctrl } = buildController()
    expect(() => ctrl.updateObject('ghost', { position: [1, 2, 3] })).not.toThrow()
    expect(scene.children).toHaveLength(0)
  })

  it('updates rotation and scale when provided', () => {
    const { scene, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    ctrl.updateObject('u1', { rotation: [0.5, 0, 0], scale: [2, 2, 2] })
    const mesh = scene.getObjectByProperty('uuid', 'u1') as THREE.Mesh
    expect(mesh.rotation.x).toBeCloseTo(0.5)
    expect(mesh.scale.x).toBe(2)
  })

  it('replaces the live material when updates.material is provided', () => {
    const { scene, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1', material: { type: 'MeshStandardMaterial', color: '#000000' } }))
    const mesh = scene.getObjectByProperty('uuid', 'u1') as THREE.Mesh
    const oldMaterial = mesh.material as THREE.Material
    const disposeSpy = vi.spyOn(oldMaterial, 'dispose')

    ctrl.updateObject('u1', { material: { type: 'MeshBasicMaterial', color: '#ff0000' } })

    expect(disposeSpy).toHaveBeenCalled()
    expect(mesh.material).not.toBe(oldMaterial)
    expect(mesh.material).toBeInstanceOf(THREE.MeshBasicMaterial)
    expect((mesh.userData as { material: { color: string } }).material.color).toBe('#ff0000')
  })
})

describe('SceneController.removeObject (cleanup)', () => {
  it('removes the uuid from the activeWindow', () => {
    const { activeWindow, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    expect(activeWindow.contains('u1')).toBe(true)
    ctrl.removeObject('u1')
    expect(activeWindow.contains('u1')).toBe(false)
  })

  it('keeps the uuid in the objectIndex (append-only by plan)', () => {
    const { objectIndex, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1', label: 'leaf' }))
    ctrl.removeObject('u1')
    expect(objectIndex.getAll()).toEqual({ u1: 'leaf' })
  })
})

describe('SceneController.removeObject', () => {
  it('removes the mesh from the scene', () => {
    const { scene, ctrl } = buildController()
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    ctrl.removeObject('u1')
    expect(scene.getObjectByProperty('uuid', 'u1')).toBeUndefined()
  })

  it('is a no-op when the uuid is unknown', () => {
    const { ctrl } = buildController()
    expect(() => ctrl.removeObject('ghost')).not.toThrow()
  })
})

describe('SceneController.addLight', () => {
  it('adds the light to the scene', () => {
    const { scene, ctrl } = buildController()
    ctrl.addLight(buildLightPayload({ uuid: 'l1' }))
    expect(scene.getObjectByProperty('uuid', 'l1')).toBeInstanceOf(THREE.Light)
  })
})

describe('SceneController.moveCamera', () => {
  it('updates camera position and target via lookAt', () => {
    const { ctrl, camera } = buildController()
    const payload: CameraMovePayload = { position: [3, 2, 5], target: [0, 0, 0] }

    const lookAtSpy = vi.spyOn(camera, 'lookAt')
    ctrl.moveCamera(payload)

    expect(camera.position.x).toBe(3)
    expect(camera.position.y).toBe(2)
    expect(camera.position.z).toBe(5)
    expect(lookAtSpy).toHaveBeenCalledWith(0, 0, 0)
  })

  it('updates fov when provided', () => {
    const { ctrl, camera } = buildController()
    const payload: CameraMovePayload = { position: [0, 0, 5], target: [0, 0, 0], fov: 75 }
    const updateSpy = vi.spyOn(camera, 'updateProjectionMatrix')

    ctrl.moveCamera(payload)

    expect(camera.fov).toBe(75)
    expect(updateSpy).toHaveBeenCalled()
  })
})

describe('SceneController animations', () => {
  it('startAnimation registers a tickable when an animationLoop is provided', () => {
    const animationLoop: AnimationLoopLike = {
      register: vi.fn(),
      unregister: vi.fn(),
    }
    const { ctrl } = buildController(animationLoop)
    ctrl.addObject(buildAddPayload({ uuid: 'u1' }))
    const payload: AnimationStartPayload = {
      uuid: 'u1',
      animationType: 'rotate',
      duration: 2,
    }
    ctrl.startAnimation(payload)
    expect(animationLoop.register).toHaveBeenCalledTimes(1)
    const tickable = (animationLoop.register as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect(tickable.uuid).toBe('u1')
  })

  it('startAnimation skips registration when the target uuid is unknown', () => {
    const animationLoop: AnimationLoopLike = {
      register: vi.fn(),
      unregister: vi.fn(),
    }
    const { ctrl } = buildController(animationLoop)
    ctrl.startAnimation({ uuid: 'ghost', animationType: 'rotate', duration: 1 })
    expect(animationLoop.register).not.toHaveBeenCalled()
  })

  it('stopAnimation unregisters by uuid', () => {
    const animationLoop: AnimationLoopLike = {
      register: vi.fn(),
      unregister: vi.fn(),
    }
    const { ctrl } = buildController(animationLoop)
    const payload: AnimationStopPayload = { uuid: 'u1' }
    ctrl.stopAnimation(payload)
    expect(animationLoop.unregister).toHaveBeenCalledWith('u1')
  })

  it('startAnimation and stopAnimation are no-ops without an animationLoop', () => {
    const { ctrl } = buildController()
    expect(() =>
      ctrl.startAnimation({ uuid: 'u1', animationType: 'rotate', duration: 1 }),
    ).not.toThrow()
    expect(() => ctrl.stopAnimation({ uuid: 'u1' })).not.toThrow()
  })
})
