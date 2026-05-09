import * as THREE from 'three'

import type { Material as MaterialSpec, ObjectAddPayload } from '@shared/schema/sceneSchema'

export const VALID_GEOMETRY_TYPES = [
  'BoxGeometry',
  'SphereGeometry',
  'CylinderGeometry',
  'ConeGeometry',
  'PlaneGeometry',
  'TorusGeometry',
  'CircleGeometry',
] as const

type GeometryCtor = new (...args: number[]) => THREE.BufferGeometry
type MaterialCtor = new (params: { color: string }) => THREE.Material

const GEOMETRY_REGISTRY: Record<string, GeometryCtor> = {
  BoxGeometry: THREE.BoxGeometry as unknown as GeometryCtor,
  SphereGeometry: THREE.SphereGeometry as unknown as GeometryCtor,
  CylinderGeometry: THREE.CylinderGeometry as unknown as GeometryCtor,
  ConeGeometry: THREE.ConeGeometry as unknown as GeometryCtor,
  PlaneGeometry: THREE.PlaneGeometry as unknown as GeometryCtor,
  TorusGeometry: THREE.TorusGeometry as unknown as GeometryCtor,
  CircleGeometry: THREE.CircleGeometry as unknown as GeometryCtor,
}

const MATERIAL_REGISTRY: Record<string, MaterialCtor> = {
  MeshStandardMaterial: THREE.MeshStandardMaterial as unknown as MaterialCtor,
  MeshBasicMaterial: THREE.MeshBasicMaterial as unknown as MaterialCtor,
  MeshPhongMaterial: THREE.MeshPhongMaterial as unknown as MaterialCtor,
  MeshLambertMaterial: THREE.MeshLambertMaterial as unknown as MaterialCtor,
  MeshPhysicalMaterial: THREE.MeshPhysicalMaterial as unknown as MaterialCtor,
}

function buildGeometry(type: string, args: number[]): THREE.BufferGeometry {
  const Ctor = GEOMETRY_REGISTRY[type]
  if (!Ctor) {
    console.warn(
      `[ObjectFactory] Unknown geometry type "${type}"; falling back to BoxGeometry`,
    )
    return new THREE.BoxGeometry()
  }
  try {
    const geom = new Ctor(...args)
    // Internal NaN sanity check only -- geometry.attributes access belongs
    // exclusively to the serializer; do NOT promote this pattern outside this fn.
    const positions = (geom as THREE.BufferGeometry).getAttribute?.('position')
    if (positions && Number.isNaN((positions.array as ArrayLike<number>)[0])) {
      throw new Error('geometry produced NaN positions')
    }
    return geom
  } catch (err) {
    console.warn(
      `[ObjectFactory] Failed to construct ${type} with args ${JSON.stringify(args)}: ${(err as Error).message}; falling back to BoxGeometry`,
    )
    return new THREE.BoxGeometry()
  }
}

export function buildMaterial(spec: MaterialSpec): THREE.Material {
  const Ctor = MATERIAL_REGISTRY[spec.type] ?? MATERIAL_REGISTRY.MeshStandardMaterial
  return new Ctor({ color: spec.color })
}

export class ObjectFactory {
  static create(payload: ObjectAddPayload): THREE.Mesh {
    const geometry = buildGeometry(payload.geometryType, payload.geometryArgs)
    const material = buildMaterial(payload.material)
    const mesh = new THREE.Mesh(geometry, material)

    mesh.uuid = payload.uuid
    mesh.position.set(payload.position[0], payload.position[1], payload.position[2])
    if (payload.rotation) {
      mesh.rotation.set(payload.rotation[0], payload.rotation[1], payload.rotation[2])
    }
    if (payload.scale) {
      mesh.scale.set(payload.scale[0], payload.scale[1], payload.scale[2])
    }
    if (payload.visible !== undefined) {
      mesh.visible = payload.visible
    }

    // Defensive copies so caller mutations after create don't leak into userData.
    mesh.userData = {
      label: payload.label,
      geometryType: payload.geometryType,
      geometryArgs: [...payload.geometryArgs],
      stage: payload.stage,
      material: { ...payload.material },
    }

    return mesh
  }
}
