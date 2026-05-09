import { useCopilotAction } from '@copilotkit/react-core'
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
 * console.warn, so a single bad event from the agent stream cannot crash the
 * canvas.
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

const PAYLOAD_PARAM = [
  {
    name: 'payload',
    type: 'object' as const,
    description: 'Event payload matching shared/schema/sceneSchema.ts',
    required: true,
  },
]

/**
 * Registers one CopilotKit frontend action per vocabulary event. Each action's
 * handler routes through routeSceneEvent so the SceneController is the only
 * mutator of Three.js state. The hook returns void; CopilotKit consumes the
 * registrations from its provider context.
 */
export function useSceneActions(ctx: RouterContext): void {
  useCopilotAction({
    name: SCENE_OBJECT_ADD,
    description: 'Add an object to the Three.js scene',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_OBJECT_ADD, value: args.payload }, ctx)
    },
  })

  useCopilotAction({
    name: SCENE_OBJECT_UPDATE,
    description: 'Update an existing object (position/rotation/scale/material)',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_OBJECT_UPDATE, value: args.payload }, ctx)
    },
  })

  useCopilotAction({
    name: SCENE_CAMERA_MOVE,
    description: 'Move the camera (position + target, optional fov)',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_CAMERA_MOVE, value: args.payload }, ctx)
    },
  })

  useCopilotAction({
    name: SCENE_LIGHT_ADD,
    description: 'Add a light (Directional/Ambient/Point)',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_LIGHT_ADD, value: args.payload }, ctx)
    },
  })

  useCopilotAction({
    name: SCENE_ANIMATION_START,
    description: 'Start an animation (rotate, etc.) on an existing object',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_ANIMATION_START, value: args.payload }, ctx)
    },
  })

  useCopilotAction({
    name: SCENE_ANIMATION_STOP,
    description: 'Stop a running animation by uuid',
    parameters: PAYLOAD_PARAM,
    handler: (args: { [x: string]: object }) => {
      routeSceneEvent({ name: SCENE_ANIMATION_STOP, value: args.payload }, ctx)
    },
  })
}
