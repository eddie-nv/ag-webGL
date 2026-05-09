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
    objectIndex,
    activeWindow,
    animationLoop: loop,
  })

  return { scene, camera, objectIndex, activeWindow, loop, controller }
}
