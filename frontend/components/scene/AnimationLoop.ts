import type * as THREE from 'three'

export interface Tickable {
  uuid: string
  tick(delta: number): void
}

export interface AnimationLoopLike {
  register(tickable: Tickable): void
  unregister(uuid: string): void
}

/**
 * RequestAnimationFrame-driven render + tick loop. `step(delta)` is exposed so
 * tests can drive a deterministic frame without going through rAF; `start` and
 * `stop` are the production entry points.
 */
export class AnimationLoop implements AnimationLoopLike {
  private readonly tickables = new Map<string, Tickable>()
  private rafId: number | null = null
  private lastTime: number | null = null

  register(tickable: Tickable): void {
    this.tickables.set(tickable.uuid, tickable)
  }

  unregister(uuid: string): void {
    this.tickables.delete(uuid)
  }

  size(): number {
    return this.tickables.size
  }

  step(delta: number): void {
    for (const t of this.tickables.values()) {
      t.tick(delta)
    }
  }

  start(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera): void {
    const loop = (now: number): void => {
      const delta = this.lastTime === null ? 0 : (now - this.lastTime) / 1000
      this.lastTime = now
      this.step(delta)
      renderer.render(scene, camera)
      this.rafId = requestAnimationFrame(loop)
    }
    this.rafId = requestAnimationFrame(loop)
  }

  stop(): void {
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId)
      this.rafId = null
    }
    this.lastTime = null
  }
}
