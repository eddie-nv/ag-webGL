import * as THREE from 'three'

import { AnimationLoop } from '@/components/scene/AnimationLoop'
import { SceneController } from '@/components/scene/SceneController'
import { ActiveWindow } from '@/serialization/activeWindow'
import { ObjectIndex } from '@/serialization/objectIndex'

export interface SceneSetup {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  objectIndex: ObjectIndex
  activeWindow: ActiveWindow
  loop: AnimationLoop
  controller: SceneController
}

// ---- snapshot types (sent to backend on every prompt for continuity) ----

export interface SceneSnapshotObject {
  uuid: string
  label: string
  geometryType: string
  position: [number, number, number]
  rotation: [number, number, number]
  scale: [number, number, number]
  stage?: string
  materialColor?: string
}

export interface SceneSnapshotLight {
  uuid: string
  lightType: string
  color: string
  intensity: number
  position?: [number, number, number]
}

export interface SceneSnapshotCamera {
  position: [number, number, number]
  target: [number, number, number]
  fov: number
}

export interface SceneSnapshot {
  objects: SceneSnapshotObject[]
  lights: SceneSnapshotLight[]
  camera: SceneSnapshotCamera
}

/**
 * Walk the live scene and produce a JSON-safe snapshot the backend can hydrate
 * into a SceneStore. The Director reads this so a follow-up prompt
 * ("move the cube up", "remove the seed") sees the right uuids and labels.
 *
 * Reads only userData + transforms -- never touches geometry.attributes (same
 * contract as sceneSerializer in M3).
 */
export function buildSceneSnapshot(setup: SceneSetup): SceneSnapshot {
  const objects: SceneSnapshotObject[] = []
  const lights: SceneSnapshotLight[] = []

  setup.scene.traverse((node) => {
    if (node === setup.scene) return

    if ((node as THREE.Light).isLight) {
      const ud = (node.userData ?? {}) as {
        lightType?: string
        color?: string
        intensity?: number
      }
      lights.push({
        uuid: node.uuid,
        lightType: ud.lightType ?? node.type,
        color: ud.color ?? '#ffffff',
        intensity: ud.intensity ?? 1,
        position: [node.position.x, node.position.y, node.position.z],
      })
      return
    }

    if ((node as THREE.Mesh).isMesh) {
      const ud = (node.userData ?? {}) as {
        label?: string
        geometryType?: string
        stage?: string
        material?: { color?: string }
      }
      objects.push({
        uuid: node.uuid,
        label: ud.label ?? '(unlabeled)',
        geometryType: ud.geometryType ?? 'BoxGeometry',
        position: [node.position.x, node.position.y, node.position.z],
        rotation: [node.rotation.x, node.rotation.y, node.rotation.z],
        scale: [node.scale.x, node.scale.y, node.scale.z],
        stage: ud.stage,
        materialColor: ud.material?.color,
      })
    }
  })

  // Camera target isn't directly readable from THREE.Camera; reconstruct from
  // the camera's forward vector as a best-effort. Backend only needs it to
  // know that a camera state exists.
  const fwd = new THREE.Vector3()
  setup.camera.getWorldDirection(fwd)
  const target: [number, number, number] = [
    setup.camera.position.x + fwd.x,
    setup.camera.position.y + fwd.y,
    setup.camera.position.z + fwd.z,
  ]

  return {
    objects,
    lights,
    camera: {
      position: [
        setup.camera.position.x,
        setup.camera.position.y,
        setup.camera.position.z,
      ],
      target,
      fov: setup.camera.fov,
    },
  }
}

/**
 * Build the long-lived Three.js scene + helpers. Called once per page mount.
 * Lives in a shared module so SceneCanvas (renders) and SceneChat (mutates
 * via routeSceneEvent) reference the same controller instance.
 */
export function buildSceneSetup(): SceneSetup {
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#0b0d12')

  const camera = new THREE.PerspectiveCamera(50, 16 / 9, 0.1, 100)
  camera.position.set(0, 1.5, 4.5)
  camera.lookAt(0, 0.8, 0)

  const objectIndex = new ObjectIndex()
  const activeWindow = new ActiveWindow()
  const loop = new AnimationLoop()
  const controller = new SceneController({
    scene,
    camera,
    objectIndex,
    activeWindow,
    animationLoop: loop,
  })

  return { scene, camera, objectIndex, activeWindow, loop, controller }
}
