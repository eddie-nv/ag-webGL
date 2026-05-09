'use client'

import { CopilotKit } from '@copilotkit/react-core'

import { SceneChat } from '@/components/chat/SceneChat'
import { StageIndicator } from '@/components/hud/StageIndicator'
import { SceneCanvas } from '@/components/scene/SceneCanvas'

export default function Page() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="sceneAgent">
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
          <SceneCanvas />
          <StageIndicator />
        </div>
        <aside
          style={{
            borderLeft: '1px solid #1f2530',
            background: '#10141c',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <SceneChat />
        </aside>
      </main>
    </CopilotKit>
  )
}
