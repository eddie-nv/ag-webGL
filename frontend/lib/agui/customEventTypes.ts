import type {
  AnimationStartPayload,
  AnimationStopPayload,
  CameraMovePayload,
  LightAddPayload,
  ObjectAddPayload,
  ObjectUpdatePayload,
} from '@shared/schema/sceneSchema'

export const SCENE_OBJECT_ADD = 'scene:object_add' as const
export const SCENE_OBJECT_UPDATE = 'scene:object_update' as const
export const SCENE_CAMERA_MOVE = 'scene:camera_move' as const
export const SCENE_LIGHT_ADD = 'scene:light_add' as const
export const SCENE_ANIMATION_START = 'scene:animation_start' as const
export const SCENE_ANIMATION_STOP = 'scene:animation_stop' as const

export type SceneEventName =
  | typeof SCENE_OBJECT_ADD
  | typeof SCENE_OBJECT_UPDATE
  | typeof SCENE_CAMERA_MOVE
  | typeof SCENE_LIGHT_ADD
  | typeof SCENE_ANIMATION_START
  | typeof SCENE_ANIMATION_STOP

export interface SceneObjectAddEvent {
  name: typeof SCENE_OBJECT_ADD
  value: ObjectAddPayload
}

export interface SceneObjectUpdateEvent {
  name: typeof SCENE_OBJECT_UPDATE
  value: ObjectUpdatePayload
}

export interface SceneCameraMoveEvent {
  name: typeof SCENE_CAMERA_MOVE
  value: CameraMovePayload
}

export interface SceneLightAddEvent {
  name: typeof SCENE_LIGHT_ADD
  value: LightAddPayload
}

export interface SceneAnimationStartEvent {
  name: typeof SCENE_ANIMATION_START
  value: AnimationStartPayload
}

export interface SceneAnimationStopEvent {
  name: typeof SCENE_ANIMATION_STOP
  value: AnimationStopPayload
}

export type SceneEvent =
  | SceneObjectAddEvent
  | SceneObjectUpdateEvent
  | SceneCameraMoveEvent
  | SceneLightAddEvent
  | SceneAnimationStartEvent
  | SceneAnimationStopEvent

export type {
  AnimationStartPayload,
  AnimationStopPayload,
  CameraMovePayload,
  LightAddPayload,
  ObjectAddPayload,
  ObjectUpdatePayload,
}
