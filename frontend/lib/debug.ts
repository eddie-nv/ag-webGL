/**
 * Browser-side scene debug helpers.
 *
 * Toggle from DevTools console:
 *   window.SCENE_DEBUG = true   // verbose
 *   window.SCENE_DEBUG = false  // silent
 * Defaults to true in dev (`process.env.NODE_ENV !== 'production'`).
 *
 * Inspect live scene state:
 *   window.__scene.controller   // SceneController instance
 *   window.__scene.scene        // THREE.Scene
 *   window.__scene.events       // every routed event in arrival order
 */

interface SceneDebugWindow {
  SCENE_DEBUG?: boolean
  __scene?: {
    controller?: unknown
    scene?: unknown
    camera?: unknown
    events: Array<{ at: number; name: string; value: unknown }>
  }
}

function w(): SceneDebugWindow | undefined {
  return typeof window !== 'undefined' ? (window as unknown as SceneDebugWindow) : undefined
}

function enabled(): boolean {
  const win = w()
  if (win?.SCENE_DEBUG !== undefined) return win.SCENE_DEBUG
  return process.env.NODE_ENV !== 'production'
}

export function sceneLog(...args: unknown[]): void {
  if (!enabled()) return
  console.log('%c[scene]', 'color:#7ec850;font-weight:600', ...args)
}

export function sceneWarn(...args: unknown[]): void {
  console.warn('%c[scene]', 'color:#e8a23a;font-weight:600', ...args)
}

export function recordEvent(name: string, value: unknown): void {
  const win = w()
  if (!win) return
  win.__scene = win.__scene ?? { events: [] }
  win.__scene.events.push({ at: Date.now(), name, value })
}

export function exposeSceneRefs(refs: {
  controller: unknown
  scene: unknown
  camera: unknown
}): void {
  const win = w()
  if (!win) return
  win.__scene = win.__scene ?? { events: [] }
  win.__scene.controller = refs.controller
  win.__scene.scene = refs.scene
  win.__scene.camera = refs.camera
  sceneLog('window.__scene exposed:', Object.keys(win.__scene))
}
