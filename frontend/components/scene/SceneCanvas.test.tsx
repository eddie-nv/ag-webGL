import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render } from '@testing-library/react'

const hoisted = vi.hoisted(() => {
  const rendererInstance = {
    setSize: vi.fn(),
    setPixelRatio: vi.fn(),
    render: vi.fn(),
    dispose: vi.fn(),
    setClearColor: vi.fn(),
    domElement: typeof document !== 'undefined' ? document.createElement('canvas') : null,
  }
  // Regular function (not arrow) so `new` returns the explicit object.
  function WebGLRenderer() {
    return rendererInstance
  }
  return {
    rendererInstance,
    WebGLRenderer: vi.fn(WebGLRenderer),
  }
})

vi.mock('three', async () => {
  const actual = await vi.importActual<typeof import('three')>('three')
  return {
    ...actual,
    WebGLRenderer: hoisted.WebGLRenderer,
  }
})

import { AnimationLoop } from './AnimationLoop'
import { SceneCanvas } from './SceneCanvas'
import { buildSceneSetup } from '@/lib/sceneSetup'

describe('SceneCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('mounts without throwing', () => {
    const setup = buildSceneSetup()
    expect(() => render(<SceneCanvas setup={setup} />)).not.toThrow()
  })

  it('calls renderer.dispose on unmount', () => {
    const setup = buildSceneSetup()
    const { unmount } = render(<SceneCanvas setup={setup} />)
    unmount()
    expect(hoisted.rendererInstance.dispose).toHaveBeenCalled()
  })

  it('AnimationLoop.stop is called on unmount', () => {
    const stopSpy = vi.spyOn(AnimationLoop.prototype, 'stop')
    const setup = buildSceneSetup()
    const { unmount } = render(<SceneCanvas setup={setup} />)
    unmount()
    expect(stopSpy).toHaveBeenCalled()
    stopSpy.mockRestore()
  })

  it('appends a canvas element to the container', () => {
    const setup = buildSceneSetup()
    const { container } = render(<SceneCanvas setup={setup} />)
    expect(container.querySelector('canvas')).toBeTruthy()
  })
})
