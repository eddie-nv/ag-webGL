import { describe, expect, it } from 'vitest'
import { buildZoneMap } from './spatialSummary'

describe('spatialSummary', () => {
  it('returns the four canonical zones', () => {
    const zones = buildZoneMap()
    expect(Object.keys(zones).sort()).toEqual(['ground', 'lower', 'mid', 'upper'])
  })

  it('every zone exposes a yRange tuple', () => {
    const zones = buildZoneMap()
    for (const zone of Object.values(zones)) {
      expect(zone.yRange).toHaveLength(2)
      expect(typeof zone.yRange[0]).toBe('number')
      expect(typeof zone.yRange[1]).toBe('number')
    }
  })

  it('zones are contiguous along the y axis', () => {
    const zones = buildZoneMap()
    expect(zones.ground.yRange[1]).toBe(zones.lower.yRange[0])
    expect(zones.lower.yRange[1]).toBe(zones.mid.yRange[0])
    expect(zones.mid.yRange[1]).toBe(zones.upper.yRange[0])
  })
})
