'use client'

import { CopilotChat } from '@copilotkit/react-ui'
import '@copilotkit/react-ui/styles.css'

import { useSceneAgent } from '@/hooks/useSceneAgent'

export function SceneChat() {
  const { activeAgentName } = useSceneAgent()
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <header
        style={{
          padding: '0.5rem 1rem',
          borderBottom: '1px solid #1f2530',
          fontSize: '0.85rem',
          color: '#a0a8b8',
        }}
      >
        agent: {activeAgentName ?? 'idle'}
      </header>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <CopilotChat
          labels={{
            title: 'Scene Agent',
            initial: 'Describe a process to animate (e.g. "show how a tomato plant grows").',
          }}
        />
      </div>
    </div>
  )
}
