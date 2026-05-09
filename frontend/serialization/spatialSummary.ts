export interface Zone {
  yRange: [number, number]
}

export type ZoneMap = Record<string, Zone>

// MOCK: replace in v2 with bounding-box computation derived from real geometry
export function buildZoneMap(): ZoneMap {
  return {
    ground: { yRange: [-0.3, 0.0] },
    lower: { yRange: [0.0, 0.6] },
    mid: { yRange: [0.6, 1.2] },
    upper: { yRange: [1.2, 2.0] },
  }
}
