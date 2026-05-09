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

vi.mock('@copilotkit/react-core', () => ({
  useCopilotAction: vi.fn(),
  useCopilotReadable: vi.fn(),
}))

import { AnimationLoop } from './AnimationLoop'
import { SceneCanvas } from './SceneCanvas'

describe('SceneCanvas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('mounts without throwing', () => {
    expect(() => render(<SceneCanvas />)).not.toThrow()
  })

  it('calls renderer.dispose on unmount', () => {
    const { unmount } = render(<SceneCanvas />)
    unmount()
    expect(hoisted.rendererInstance.dispose).toHaveBeenCalled()
  })

  it('AnimationLoop.stop is called on unmount', () => {
    const stopSpy = vi.spyOn(AnimationLoop.prototype, 'stop')
    const { unmount } = render(<SceneCanvas />)
    unmount()
    expect(stopSpy).toHaveBeenCalled()
    stopSpy.mockRestore()
  })

  it('appends a canvas element to the container', () => {
    const { container } = render(<SceneCanvas />)
    expect(container.querySelector('canvas')).toBeTruthy()
  })
})
