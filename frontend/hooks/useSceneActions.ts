import type * as THREE from 'three'

import {
  AnimationStartSchema,
  AnimationStopSchema,
  CameraMoveSchema,
  LightAddSchema,
  ObjectAddSchema,
  ObjectUpdateSchema,
} from '@shared/schema/sceneSchema'
import {
  SCENE_ANIMATION_START,
  SCENE_ANIMATION_STOP,
  SCENE_CAMERA_MOVE,
  SCENE_LIGHT_ADD,
  SCENE_OBJECT_ADD,
  SCENE_OBJECT_UPDATE,
} from '@/lib/agui/customEventTypes'
import { recordEvent, sceneLog, sceneWarn } from '@/lib/debug'
import type { SceneController } from '@/components/scene/SceneController'

export interface RouterContext {
  controller: SceneController
  camera: THREE.Camera
}

export interface RawSceneEvent {
  name: string
  value: unknown
}

/**
 * Pure dispatcher from a SceneEvent to the matching SceneController method.
 * Validates the payload via Zod and silently drops malformed events with a
 * sceneWarn -- a single bad event from the agent stream cannot crash the
 * canvas. Called from SceneChat as it parses the AG-UI SSE stream.
 */
export function routeSceneEvent(event: RawSceneEvent, ctx: RouterContext): void {
  sceneLog('event in:', event.name, event.value)
  recordEvent(event.name, event.value)

  switch (event.name) {
    case SCENE_OBJECT_ADD: {
      const parsed = ObjectAddSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      sceneLog('-> controller.addObject', parsed.data.uuid, parsed.data.label)
      ctx.controller.addObject(parsed.data)
      return
    }
    case SCENE_OBJECT_UPDATE: {
      const parsed = ObjectUpdateSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      const { uuid, ...updates } = parsed.data
      sceneLog('-> controller.updateObject', uuid, updates)
      ctx.controller.updateObject(uuid, updates)
      return
    }
    case SCENE_CAMERA_MOVE: {
      const parsed = CameraMoveSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      sceneLog('-> controller.moveCamera', parsed.data)
      ctx.controller.moveCamera(parsed.data, ctx.camera)
      return
    }
    case SCENE_LIGHT_ADD: {
      const parsed = LightAddSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      sceneLog('-> controller.addLight', parsed.data.uuid, parsed.data.lightType)
      ctx.controller.addLight(parsed.data)
      return
    }
    case SCENE_ANIMATION_START: {
      const parsed = AnimationStartSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      sceneLog('-> controller.startAnimation', parsed.data.uuid)
      ctx.controller.startAnimation(parsed.data)
      return
    }
    case SCENE_ANIMATION_STOP: {
      const parsed = AnimationStopSchema.safeParse(event.value)
      if (!parsed.success) {
        warn(event.name, parsed.error.message)
        return
      }
      sceneLog('-> controller.stopAnimation', parsed.data.uuid)
      ctx.controller.stopAnimation(parsed.data)
      return
    }
    default:
      sceneWarn('unhandled event name:', event.name)
      return
  }
}

function warn(eventName: string, detail: string): void {
  sceneWarn(`invalid ${eventName} payload:`, detail)
}
