import * as THREE from 'three'

import type { LightAddPayload } from '@shared/schema/sceneSchema'

export const VALID_LIGHT_TYPES = ['DirectionalLight', 'AmbientLight', 'PointLight'] as const

export class LightFactory {
  static create(payload: LightAddPayload): THREE.Light {
    const lightType = payload.lightType as string
    let light: THREE.Light

    if (lightType === 'DirectionalLight') {
      light = new THREE.DirectionalLight(payload.color, payload.intensity)
    } else if (lightType === 'AmbientLight') {
      light = new THREE.AmbientLight(payload.color, payload.intensity)
    } else if (lightType === 'PointLight') {
      light = new THREE.PointLight(payload.color, payload.intensity)
    } else {
      console.warn(
        `[LightFactory] Unknown light type "${lightType}"; falling back to AmbientLight`,
      )
      light = new THREE.AmbientLight(payload.color, payload.intensity)
    }

    light.uuid = payload.uuid
    if (payload.position) {
      light.position.set(payload.position[0], payload.position[1], payload.position[2])
    }
    light.userData = {
      lightType,
      color: payload.color,
      intensity: payload.intensity,
    }

    return light
  }
}
