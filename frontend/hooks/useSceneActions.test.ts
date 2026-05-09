import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import * as THREE from 'three'

import type {
  AnimationStartPayload,
  CameraMovePayload,
  LightAddPayload,
  ObjectAddPayload,
} from '@shared/schema/sceneSchema'
import {
  SCENE_ANIMATION_START,
  SCENE_ANIMATION_STOP,
  SCENE_CAMERA_MOVE,
  SCENE_LIGHT_ADD,
  SCENE_OBJECT_ADD,
  SCENE_OBJECT_UPDATE,
} from '@/lib/agui/customEventTypes'
import { ActiveWindow } from '@/serialization/activeWindow'
import { ObjectIndex } from '@/serialization/objectIndex'
import { SceneController } from '@/components/scene/SceneController'

import { routeSceneEvent, type RouterContext } from './useSceneActions'

function buildCtx(): RouterContext {
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100)
  const objectIndex = new ObjectIndex()
  const activeWindow = new ActiveWindow()
  const controller = new SceneController({ scene, objectIndex, activeWindow })
  return { controller, camera }
}

const validObjectAdd: ObjectAddPayload = {
  uuid: 'u1',
  label: 'leaf',
  geometryType: 'BoxGeometry',
  geometryArgs: [1, 1, 1],
  material: { type: 'MeshStandardMaterial', color: '#5b3a1a' },
  position: [0, 1, 0],
  stage: 'growth',
}

const validCameraMove: CameraMovePayload = {
  position: [3, 2, 5],
  target: [0, 0, 0],
}

const validLightAdd: LightAddPayload = {
  uuid: 'l1',
  lightType: 'DirectionalLight',
  color: '#ffffff',
  intensity: 1.0,
}

const validAnimationStart: AnimationStartPayload = {
  uuid: 'u1',
  animationType: 'rotate',
  duration: 2,
}

describe('routeSceneEvent', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('scene:object_add calls controller.addObject', () => {
    const ctx = buildCtx()
    const spy = vi.spyOn(ctx.controller, 'addObject')

    routeSceneEvent({ name: SCENE_OBJECT_ADD, value: validObjectAdd }, ctx)

    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy.mock.calls[0][0].uuid).toBe('u1')
  })

  it('scene:camera_move calls controller.moveCamera', () => {
    const ctx = buildCtx()
    const spy = vi.spyOn(ctx.controller, 'moveCamera')

    routeSceneEvent({ name: SCENE_CAMERA_MOVE, value: validCameraMove }, ctx)

    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy.mock.calls[0][1]).toBe(ctx.camera)
  })

  it('scene:light_add calls controller.addLight', () => {
    const ctx = buildCtx()
    const spy = vi.spyOn(ctx.controller, 'addLight')

    routeSceneEvent({ name: SCENE_LIGHT_ADD, value: validLightAdd }, ctx)

    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('scene:animation_start calls controller.startAnimation', () => {
    const ctx = buildCtx()
    ctx.controller.addObject(validObjectAdd)
    const spy = vi.spyOn(ctx.controller, 'startAnimation')

    routeSceneEvent({ name: SCENE_ANIMATION_START, value: validAnimationStart }, ctx)

    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('scene:animation_stop calls controller.stopAnimation', () => {
    const ctx = buildCtx()
    const spy = vi.spyOn(ctx.controller, 'stopAnimation')

    routeSceneEvent({ name: SCENE_ANIMATION_STOP, value: { uuid: 'u1' } }, ctx)

    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('scene:object_update calls controller.updateObject with uuid + updates', () => {
    const ctx = buildCtx()
    ctx.controller.addObject(validObjectAdd)
    const spy = vi.spyOn(ctx.controller, 'updateObject')

    routeSceneEvent(
      { name: SCENE_OBJECT_UPDATE, value: { uuid: 'u1', position: [5, 5, 5] } },
      ctx,
    )

    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy.mock.calls[0][0]).toBe('u1')
    expect(spy.mock.calls[0][1]).toEqual({ position: [5, 5, 5] })
  })

  it('malformed payload does not throw and warns', () => {
    const ctx = buildCtx()
    const addSpy = vi.spyOn(ctx.controller, 'addObject')

    expect(() =>
      routeSceneEvent({ name: SCENE_OBJECT_ADD, value: { not: 'valid' } }, ctx),
    ).not.toThrow()

    expect(addSpy).not.toHaveBeenCalled()
    expect(warnSpy).toHaveBeenCalled()
  })

  it('unknown event name is a silent no-op', () => {
    const ctx = buildCtx()
    expect(() =>
      routeSceneEvent({ name: 'scene:unknown_event', value: {} }, ctx),
    ).not.toThrow()
  })

  it('object_update with missing uuid does not throw', () => {
    const ctx = buildCtx()
    const spy = vi.spyOn(ctx.controller, 'updateObject')

    expect(() =>
      routeSceneEvent(
        { name: SCENE_OBJECT_UPDATE, value: { position: [1, 2, 3] } },
        ctx,
      ),
    ).not.toThrow()

    expect(spy).not.toHaveBeenCalled()
  })
})
