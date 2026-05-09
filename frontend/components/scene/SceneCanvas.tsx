'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

import { ActiveWindow } from '@/serialization/activeWindow'
import { ObjectIndex } from '@/serialization/objectIndex'
import { exposeSceneRefs, sceneLog } from '@/lib/debug'
import { useSceneActions } from '@/hooks/useSceneActions'
import { useSceneReadable } from '@/hooks/useSceneReadable'

import { AnimationLoop } from './AnimationLoop'
import { SceneController } from './SceneController'

interface SceneSetup {
  scene: THREE.Scene
  camera: THREE.PerspectiveCamera
  objectIndex: ObjectIndex
  activeWindow: ActiveWindow
  loop: AnimationLoop
  controller: SceneController
}

function buildSetup(): SceneSetup {
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

export function SceneCanvas() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const setupRef = useRef<SceneSetup | null>(null)

  if (setupRef.current === null) {
    setupRef.current = buildSetup()
  }
  const setup = setupRef.current

  useSceneActions({ controller: setup.controller, camera: setup.camera })
  useSceneReadable(setup.scene, {
    objectIndex: setup.objectIndex,
    activeWindow: setup.activeWindow,
  })

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    const resize = () => {
      const width = container.clientWidth || window.innerWidth
      const height = container.clientHeight || window.innerHeight
      renderer.setSize(width, height)
      setup.camera.aspect = width / height
      setup.camera.updateProjectionMatrix()
    }
    resize()
    container.appendChild(renderer.domElement)
    window.addEventListener('resize', resize)

    sceneLog('canvas mounted', `${container.clientWidth}x${container.clientHeight}`)
    exposeSceneRefs({
      controller: setup.controller,
      scene: setup.scene,
      camera: setup.camera,
    })

    setup.loop.start(renderer, setup.scene, setup.camera)

    return () => {
      window.removeEventListener('resize', resize)
      setup.loop.stop()
      renderer.dispose()
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement)
      }
    }
  }, [setup])

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
}
