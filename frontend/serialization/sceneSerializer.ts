import type { Object3D } from 'three'

import type { ActiveWindow } from './activeWindow'
import type { ObjectIndex } from './objectIndex'
import { buildZoneMap, type ZoneMap } from './spatialSummary'

export interface SerializedMaterial {
  type: string
  color: string
  hasTexture: boolean
}

export interface SerializedObject {
  uuid: string
  label: string
  geometryType: string
  geometryArgs: number[]
  position: [number, number, number]
  rotation: [number, number, number]
  scale: [number, number, number]
  visible: boolean
  stage?: string
  material: SerializedMaterial
}

export interface SerializedScene {
  activeWindow: SerializedObject[]
  fullIndex: Record<string, string>
  spatialSummary: ZoneMap
  objectCount: number
}

export interface SerializerContext {
  objectIndex: ObjectIndex
  activeWindow: ActiveWindow
}

interface ObjectUserData {
  label?: string
  stage?: string
  geometryType?: string
  geometryArgs?: number[]
  material?: { type?: string; color?: string }
}

interface MaterialLike {
  type?: string
  color?: { getStyle?: () => string } | string
  map?: unknown
}

function readUserData(obj: Object3D): ObjectUserData {
  return (obj.userData ?? {}) as ObjectUserData
}

function readMaterial(obj: Object3D): MaterialLike | undefined {
  const candidate = (obj as { material?: MaterialLike | MaterialLike[] }).material
  if (Array.isArray(candidate)) return candidate[0]
  return candidate
}

function hasTexture(material: MaterialLike | undefined): boolean {
  if (!material) return false
  return material.map !== undefined && material.map !== null
}

function materialColor(userData: ObjectUserData, material: MaterialLike | undefined): string {
  if (userData.material?.color) return userData.material.color
  const color = material?.color
  if (typeof color === 'string') return color
  if (color && typeof color.getStyle === 'function') return color.getStyle()
  return '#ffffff'
}

function materialType(userData: ObjectUserData, material: MaterialLike | undefined): string {
  return userData.material?.type ?? material?.type ?? 'unknown'
}

function serializeObject(obj: Object3D): SerializedObject {
  const ud = readUserData(obj)
  const mat = readMaterial(obj)
  return {
    uuid: obj.uuid,
    label: ud.label ?? '(unlabeled)',
    geometryType: ud.geometryType ?? 'BoxGeometry',
    geometryArgs: ud.geometryArgs ?? [],
    position: [obj.position.x, obj.position.y, obj.position.z],
    rotation: [obj.rotation.x, obj.rotation.y, obj.rotation.z],
    scale: [obj.scale.x, obj.scale.y, obj.scale.z],
    visible: obj.visible,
    stage: ud.stage,
    material: {
      type: materialType(ud, mat),
      color: materialColor(ud, mat),
      hasTexture: hasTexture(mat),
    },
  }
}

/**
 * Walks the scene reading only userData and current transforms. Never calls
 * toJSON, never reads geometry.attributes, never embeds texture data.
 */
export function serializeScene(scene: Object3D, ctx: SerializerContext): SerializedScene {
  const active: SerializedObject[] = []
  let objectCount = 0

  scene.traverse((obj) => {
    if (obj === scene) return
    objectCount += 1
    if (ctx.activeWindow.contains(obj.uuid)) {
      active.push(serializeObject(obj))
    }
  })

  return {
    activeWindow: active,
    fullIndex: ctx.objectIndex.getAll(),
    spatialSummary: buildZoneMap(),
    objectCount,
  }
}
