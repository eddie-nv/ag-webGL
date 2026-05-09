'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

import { exposeSceneRefs, sceneLog } from '@/lib/debug'
import type { SceneSetup } from '@/lib/sceneSetup'

interface Props {
  setup: SceneSetup
}

/**
 * Mounts the WebGLRenderer onto a div, drives the animation loop, and exposes
 * the controller/scene/camera on window.__scene for DevTools probing.
 *
 * Setup is owned by ScenePage so SceneChat can dispatch routeSceneEvent into
 * the same controller. Pure rendering surface here.
 */
export function SceneCanvas({ setup }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)

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
