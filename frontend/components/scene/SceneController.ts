import * as THREE from 'three'

import type {
  AnimationStartPayload,
  AnimationStopPayload,
  CameraMovePayload,
  LightAddPayload,
  ObjectAddPayload,
  ObjectUpdatePayload,
} from '@shared/schema/sceneSchema'
import { CAMERA_ANIMATION_UUID } from '@/lib/agui/customEventTypes'
import { ActiveWindow } from '@/serialization/activeWindow'
import { ObjectIndex } from '@/serialization/objectIndex'

import { LightFactory } from './objects/LightFactory'
import { ObjectFactory, buildMaterial } from './objects/ObjectFactory'

export type { AnimationLoopLike, Tickable } from './AnimationLoop'
import type { AnimationLoopLike, Tickable } from './AnimationLoop'

export interface SceneControllerOptions {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  objectIndex: ObjectIndex
  activeWindow: ActiveWindow
  animationLoop?: AnimationLoopLike
}

export type ObjectUpdates = Omit<ObjectUpdatePayload, 'uuid'>

interface DisposableMaterial extends THREE.Material {
  dispose(): void
}

interface DisposableGeometry extends THREE.BufferGeometry {
  dispose(): void
}

export class SceneController {
  private readonly scene: THREE.Scene
  private readonly camera: THREE.PerspectiveCamera
  private readonly objectIndex: ObjectIndex
  private readonly activeWindow: ActiveWindow
  private readonly animationLoop?: AnimationLoopLike
  // Camera lookAt target tracked for orbit animations -- THREE.Camera doesn't
  // expose lookAt as readable state, so we record it on every moveCamera call.
  private cameraTarget: THREE.Vector3 = new THREE.Vector3(0, 0.8, 0)

  constructor(opts: SceneControllerOptions) {
    this.scene = opts.scene
    this.camera = opts.camera
    this.objectIndex = opts.objectIndex
    this.activeWindow = opts.activeWindow
    this.animationLoop = opts.animationLoop
  }

  addObject(payload: ObjectAddPayload): void {
    const mesh = ObjectFactory.create(payload)
    this.scene.add(mesh)
    this.objectIndex.add(payload.uuid, payload.label)
    this.activeWindow.push(payload.uuid)
  }

  updateObject(uuid: string, updates: ObjectUpdates): void {
    const obj = this.scene.getObjectByProperty('uuid', uuid)
    if (!obj) return
    if (updates.position) {
      obj.position.set(updates.position[0], updates.position[1], updates.position[2])
    }
    if (updates.rotation) {
      obj.rotation.set(updates.rotation[0], updates.rotation[1], updates.rotation[2])
    }
    if (updates.scale) {
      obj.scale.set(updates.scale[0], updates.scale[1], updates.scale[2])
    }
    if (updates.material) {
      const mesh = obj as THREE.Mesh
      const previous = mesh.material
      if (previous && !Array.isArray(previous)) {
        ;(previous as THREE.Material).dispose?.()
      }
      mesh.material = buildMaterial(updates.material)
      mesh.userData = { ...mesh.userData, material: { ...updates.material } }
    }
    this.activeWindow.push(uuid)
  }

  removeObject(uuid: string): void {
    const obj = this.scene.getObjectByProperty('uuid', uuid)
    if (!obj) return
    this.scene.remove(obj)
    this.disposeObject(obj)
    this.activeWindow.remove(uuid)
    // objectIndex is append-only by plan -- the uuid stays in fullIndex so the
    // agent retains historical identity. (See PLAN.md M3.)
  }

  addLight(payload: LightAddPayload): void {
    const light = LightFactory.create(payload)
    this.scene.add(light)
  }

  moveCamera(payload: CameraMovePayload): void {
    this.camera.position.set(payload.position[0], payload.position[1], payload.position[2])
    this.camera.lookAt(payload.target[0], payload.target[1], payload.target[2])
    this.cameraTarget.set(payload.target[0], payload.target[1], payload.target[2])
    if (payload.fov !== undefined) {
      this.camera.fov = payload.fov
      this.camera.updateProjectionMatrix()
    }
  }

  startAnimation(payload: AnimationStartPayload): void {
    if (!this.animationLoop) return

    if (payload.uuid === CAMERA_ANIMATION_UUID) {
      this.animationLoop.register(buildCameraOrbitTickable(payload, this.camera, this.cameraTarget))
      return
    }

    const target = this.scene.getObjectByProperty('uuid', payload.uuid)
    if (!target) return
    this.animationLoop.register(buildObjectTickable(payload, target))
  }

  stopAnimation(payload: AnimationStopPayload): void {
    if (!this.animationLoop) return
    this.animationLoop.unregister(payload.uuid)
  }

  private disposeObject(obj: THREE.Object3D): void {
    const mesh = obj as THREE.Mesh
    const geom = mesh.geometry as DisposableGeometry | undefined
    geom?.dispose?.()
    const mat = mesh.material as DisposableMaterial | DisposableMaterial[] | undefined
    if (Array.isArray(mat)) {
      for (const m of mat) m?.dispose?.()
    } else {
      mat?.dispose?.()
    }
  }
}

function buildObjectTickable(payload: AnimationStartPayload, target: THREE.Object3D): Tickable {
  // V1 supports a single rotation animation; richer animation composition is v2.
  const axis = (payload.axis ?? 'y') as 'x' | 'y' | 'z'
  const speed = payload.duration > 0 ? (Math.PI * 2) / payload.duration : 0

  return {
    uuid: payload.uuid,
    tick(delta: number) {
      if (payload.animationType === 'rotate') {
        target.rotation[axis] += speed * delta
      }
    },
  }
}

function buildCameraOrbitTickable(
  payload: AnimationStartPayload,
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
): Tickable {
  const speed = payload.duration > 0 ? (Math.PI * 2) / payload.duration : 0
  // Capture initial offset (camera relative to target) so we orbit around it
  // at constant radius rather than translating the camera arbitrarily.
  const offset = camera.position.clone().sub(target)
  const radius = Math.hypot(offset.x, offset.z)
  const initialAngle = Math.atan2(offset.x, offset.z)
  const initialY = camera.position.y
  let elapsed = 0

  return {
    uuid: payload.uuid,
    tick(delta: number) {
      elapsed += delta
      const angle = initialAngle + speed * elapsed
      camera.position.x = target.x + radius * Math.sin(angle)
      camera.position.z = target.z + radius * Math.cos(angle)
      camera.position.y = initialY
      camera.lookAt(target)
    },
  }
}
