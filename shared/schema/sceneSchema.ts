import { z } from 'zod'

export const Vec3Schema = z.tuple([z.number(), z.number(), z.number()])
export type Vec3 = z.infer<typeof Vec3Schema>

export const MaterialSchema = z.object({
  type: z.string(),
  color: z.string(),
})
export type Material = z.infer<typeof MaterialSchema>

export const ObjectAddSchema = z.object({
  uuid: z.string(),
  label: z.string(),
  geometryType: z.string(),
  geometryArgs: z.array(z.number()),
  material: MaterialSchema,
  position: Vec3Schema,
  stage: z.string(),
  rotation: Vec3Schema.optional(),
  scale: Vec3Schema.optional(),
  visible: z.boolean().optional(),
})
export type ObjectAddPayload = z.infer<typeof ObjectAddSchema>

export const ObjectUpdateSchema = z.object({
  uuid: z.string(),
  position: Vec3Schema.optional(),
  rotation: Vec3Schema.optional(),
  scale: Vec3Schema.optional(),
  material: MaterialSchema.optional(),
})
export type ObjectUpdatePayload = z.infer<typeof ObjectUpdateSchema>

export const CameraMoveSchema = z.object({
  position: Vec3Schema,
  target: Vec3Schema,
  fov: z.number().optional(),
})
export type CameraMovePayload = z.infer<typeof CameraMoveSchema>

export const LightTypeSchema = z.enum(['DirectionalLight', 'AmbientLight', 'PointLight'])
export type LightType = z.infer<typeof LightTypeSchema>

export const LightAddSchema = z.object({
  uuid: z.string(),
  lightType: LightTypeSchema,
  color: z.string(),
  intensity: z.number(),
  position: Vec3Schema.optional(),
})
export type LightAddPayload = z.infer<typeof LightAddSchema>

export const AnimationStartSchema = z.object({
  uuid: z.string(),
  animationType: z.string(),
  duration: z.number(),
  axis: z.string().optional(),
  from: Vec3Schema.optional(),
  to: Vec3Schema.optional(),
  loop: z.boolean().optional(),
  easing: z.string().optional(),
})
export type AnimationStartPayload = z.infer<typeof AnimationStartSchema>

export const AnimationStopSchema = z.object({
  uuid: z.string(),
})
export type AnimationStopPayload = z.infer<typeof AnimationStopSchema>
