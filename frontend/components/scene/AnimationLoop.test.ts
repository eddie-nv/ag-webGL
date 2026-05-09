import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import * as THREE from 'three'

import { AnimationLoop } from './AnimationLoop'

describe('AnimationLoop register/unregister', () => {
  it('register adds object to updatables', () => {
    const loop = new AnimationLoop()
    loop.register({ uuid: 'u1', tick: () => {} })
    expect(loop.size()).toBe(1)
  })

  it('unregister removes object by uuid', () => {
    const loop = new AnimationLoop()
    loop.register({ uuid: 'u1', tick: () => {} })
    loop.unregister('u1')
    expect(loop.size()).toBe(0)
  })

  it('unregister on unknown uuid is a no-op', () => {
    const loop = new AnimationLoop()
    expect(() => loop.unregister('ghost')).not.toThrow()
  })

  it('registering same uuid twice does not duplicate', () => {
    const loop = new AnimationLoop()
    loop.register({ uuid: 'u1', tick: () => {} })
    loop.register({ uuid: 'u1', tick: () => {} })
    expect(loop.size()).toBe(1)
  })
})

describe('AnimationLoop step', () => {
  it('tick is called on all registered objects', () => {
    const loop = new AnimationLoop()
    const a = vi.fn()
    const b = vi.fn()
    loop.register({ uuid: 'u1', tick: a })
    loop.register({ uuid: 'u2', tick: b })

    loop.step(0.016)

    expect(a).toHaveBeenCalledTimes(1)
    expect(b).toHaveBeenCalledTimes(1)
  })

  it('tick receives delta time argument', () => {
    const loop = new AnimationLoop()
    const tickFn = vi.fn()
    loop.register({ uuid: 'u1', tick: tickFn })

    loop.step(0.033)

    expect(tickFn).toHaveBeenCalledWith(0.033)
  })
})

describe('AnimationLoop start/stop', () => {
  let rafSpy: ReturnType<typeof vi.spyOn>
  let cafSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    rafSpy = vi.spyOn(globalThis, 'requestAnimationFrame').mockReturnValue(1 as unknown as number)
    cafSpy = vi.spyOn(globalThis, 'cancelAnimationFrame').mockImplementation(() => {})
  })

  afterEach(() => {
    rafSpy.mockRestore()
    cafSpy.mockRestore()
  })

  it('start schedules the first frame via requestAnimationFrame', () => {
    const loop = new AnimationLoop()
    const renderer = { render: vi.fn() } as unknown as THREE.WebGLRenderer
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera()

    loop.start(renderer, scene, camera)

    expect(rafSpy).toHaveBeenCalled()
  })

  it('stop cancels the scheduled frame', () => {
    const loop = new AnimationLoop()
    const renderer = { render: vi.fn() } as unknown as THREE.WebGLRenderer
    loop.start(renderer, new THREE.Scene(), new THREE.PerspectiveCamera())

    loop.stop()

    expect(cafSpy).toHaveBeenCalled()
  })

  it('stop is idempotent when not running', () => {
    const loop = new AnimationLoop()
    expect(() => loop.stop()).not.toThrow()
  })
})
