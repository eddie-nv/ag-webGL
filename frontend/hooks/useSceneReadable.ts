import { useCopilotReadable } from '@copilotkit/react-core'
import type * as THREE from 'three'

import {
  serializeScene,
  type SerializedScene,
  type SerializerContext,
} from '@/serialization/sceneSerializer'

/**
 * Builds the hybrid scene payload the agent sees as readable context.
 * Pure (no React/CopilotKit) so it stays trivially testable.
 */
export function buildReadablePayload(
  scene: THREE.Object3D,
  ctx: SerializerContext,
): SerializedScene {
  return serializeScene(scene, ctx)
}

/**
 * Pushes the SerializedScene to CopilotKit's readable context. The agent sees
 * activeWindow (recently mutated, full state), fullIndex (uuid->label for
 * everything), spatialSummary (zone map), and objectCount.
 */
export function useSceneReadable(scene: THREE.Object3D, ctx: SerializerContext): void {
  const payload = buildReadablePayload(scene, ctx)
  useCopilotReadable({
    description:
      'Scene state: activeWindow contains recently mutated objects with full ' +
      'detail; fullIndex is uuid->label for every object; spatialSummary is ' +
      'the zone map (ground/lower/mid/upper).',
    value: payload,
  })
}
