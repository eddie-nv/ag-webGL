'use client'

import { useRef } from 'react'

import { SceneChat } from '@/components/chat/SceneChat'
import { StageIndicator } from '@/components/hud/StageIndicator'
import { SceneCanvas } from '@/components/scene/SceneCanvas'
import { buildSceneSetup, type SceneSetup } from '@/lib/sceneSetup'

export function ScenePage() {
  const setupRef = useRef<SceneSetup | null>(null)
  if (setupRef.current === null) {
    setupRef.current = buildSceneSetup()
  }
  const setup = setupRef.current

  return (
    <main
      style={{
        display: 'grid',
        gridTemplateColumns: '1fr 360px',
        height: '100vh',
        width: '100vw',
        background: '#0b0d12',
        color: '#cdd5e0',
      }}
    >
      <div style={{ position: 'relative' }}>
        <SceneCanvas setup={setup} />
        <StageIndicator />
      </div>
      <SceneChat setup={setup} />
    </main>
  )
}
