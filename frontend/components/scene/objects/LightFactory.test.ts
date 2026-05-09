import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import * as THREE from 'three'

import type { LightAddPayload } from '@shared/schema/sceneSchema'
import { LightFactory } from './LightFactory'

function buildPayload(overrides: Partial<LightAddPayload> = {}): LightAddPayload {
  return {
    uuid: 'l1',
    lightType: 'DirectionalLight',
    color: '#ffffff',
    intensity: 1.0,
    ...overrides,
  }
}

describe('LightFactory', () => {
  let warnSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
  })

  afterEach(() => {
    warnSpy.mockRestore()
  })

  it('creates a DirectionalLight with payload uuid, color, intensity', () => {
    const light = LightFactory.create(buildPayload({ intensity: 2.5 }))
    expect(light).toBeInstanceOf(THREE.DirectionalLight)
    expect(light.uuid).toBe('l1')
    expect(light.intensity).toBe(2.5)
  })

  it('creates an AmbientLight', () => {
    const light = LightFactory.create(buildPayload({ lightType: 'AmbientLight' }))
    expect(light).toBeInstanceOf(THREE.AmbientLight)
  })

  it('creates a PointLight', () => {
    const light = LightFactory.create(buildPayload({ lightType: 'PointLight' }))
    expect(light).toBeInstanceOf(THREE.PointLight)
  })

  it('falls back to AmbientLight for unknown light types', () => {
    const light = LightFactory.create(buildPayload({
      lightType: 'SpotLight' as unknown as LightAddPayload['lightType'],
    }))
    expect(light).toBeInstanceOf(THREE.AmbientLight)
    expect(warnSpy).toHaveBeenCalled()
  })

  it('tags userData with lightType', () => {
    const light = LightFactory.create(buildPayload({ lightType: 'PointLight' }))
    expect(light.userData.lightType).toBe('PointLight')
  })

  it('applies position when provided', () => {
    const light = LightFactory.create(buildPayload({ lightType: 'PointLight', position: [1, 2, 3] }))
    expect(light.position.x).toBe(1)
    expect(light.position.y).toBe(2)
    expect(light.position.z).toBe(3)
  })
})
