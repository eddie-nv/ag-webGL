import { describe, expect, it } from 'vitest'
import {
  ObjectAddSchema,
  ObjectUpdateSchema,
  CameraMoveSchema,
  LightAddSchema,
  AnimationStartSchema,
  AnimationStopSchema,
} from '@shared/schema/sceneSchema'
import {
  SCENE_OBJECT_ADD,
  SCENE_OBJECT_UPDATE,
  SCENE_CAMERA_MOVE,
  SCENE_LIGHT_ADD,
  SCENE_ANIMATION_START,
  SCENE_ANIMATION_STOP,
} from '@/lib/agui/customEventTypes'

const validObjectAdd = {
  uuid: 'obj-1',
  label: 'tomato_seed',
  geometryType: 'SphereGeometry',
  geometryArgs: [0.05, 16, 16],
  material: { type: 'MeshStandardMaterial', color: '#5b3a1a' },
  position: [0, -0.1, 0],
  stage: 'germination',
}

describe('object_add payload', () => {
  it('matches schema with all required fields', () => {
    expect(ObjectAddSchema.safeParse(validObjectAdd).success).toBe(true)
  })

  it('fails validation when uuid is missing', () => {
    const { uuid: _omit, ...withoutUuid } = validObjectAdd
    expect(ObjectAddSchema.safeParse(withoutUuid).success).toBe(false)
  })

  it('fails validation when geometryType is missing', () => {
    const { geometryType: _omit, ...withoutType } = validObjectAdd
    expect(ObjectAddSchema.safeParse(withoutType).success).toBe(false)
  })

  it('fails validation when position is not 3-tuple', () => {
    expect(
      ObjectAddSchema.safeParse({ ...validObjectAdd, position: [0, 0] }).success,
    ).toBe(false)
  })
})

describe('object_update payload', () => {
  it('requires uuid only', () => {
    expect(ObjectUpdateSchema.safeParse({ uuid: 'obj-1' }).success).toBe(true)
  })

  it('fails validation when uuid is missing', () => {
    expect(ObjectUpdateSchema.safeParse({ position: [1, 2, 3] }).success).toBe(false)
  })
})

describe('camera_move payload', () => {
  it('passes with both position and target', () => {
    expect(
      CameraMoveSchema.safeParse({ position: [3, 2, 5], target: [0, 0, 0] }).success,
    ).toBe(true)
  })

  it('fails validation when target is missing', () => {
    expect(CameraMoveSchema.safeParse({ position: [0, 0, 0] }).success).toBe(false)
  })

  it('fails validation when position is missing', () => {
    expect(CameraMoveSchema.safeParse({ target: [0, 0, 0] }).success).toBe(false)
  })
})

describe('light_add payload', () => {
  const valid = {
    uuid: 'light-1',
    lightType: 'DirectionalLight' as const,
    color: '#ffffff',
    intensity: 1.2,
  }

  it('accepts DirectionalLight, AmbientLight, PointLight', () => {
    expect(LightAddSchema.safeParse(valid).success).toBe(true)
    expect(LightAddSchema.safeParse({ ...valid, lightType: 'AmbientLight' }).success).toBe(true)
    expect(LightAddSchema.safeParse({ ...valid, lightType: 'PointLight' }).success).toBe(true)
  })

  it('rejects unknown light types', () => {
    expect(LightAddSchema.safeParse({ ...valid, lightType: 'SpotLight' }).success).toBe(false)
  })
})

describe('animation_start payload', () => {
  it('requires duration', () => {
    expect(
      AnimationStartSchema.safeParse({ uuid: 'obj-1', animationType: 'rotate' }).success,
    ).toBe(false)
    expect(
      AnimationStartSchema.safeParse({
        uuid: 'obj-1',
        animationType: 'rotate',
        duration: 2.0,
      }).success,
    ).toBe(true)
  })
})

describe('animation_stop payload', () => {
  it('requires uuid', () => {
    expect(AnimationStopSchema.safeParse({}).success).toBe(false)
    expect(AnimationStopSchema.safeParse({ uuid: 'obj-1' }).success).toBe(true)
  })
})

describe('event name constants', () => {
  it('match the AG-UI vocabulary strings', () => {
    expect(SCENE_OBJECT_ADD).toBe('scene:object_add')
    expect(SCENE_OBJECT_UPDATE).toBe('scene:object_update')
    expect(SCENE_CAMERA_MOVE).toBe('scene:camera_move')
    expect(SCENE_LIGHT_ADD).toBe('scene:light_add')
    expect(SCENE_ANIMATION_START).toBe('scene:animation_start')
    expect(SCENE_ANIMATION_STOP).toBe('scene:animation_stop')
  })
})
