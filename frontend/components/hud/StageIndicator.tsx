'use client'

import { useSceneAgent } from '@/hooks/useSceneAgent'

export function StageIndicator() {
  const { currentStage, activeAgentName } = useSceneAgent()
  if (!currentStage && !activeAgentName) return null

  return (
    <div
      style={{
        position: 'absolute',
        top: '1rem',
        left: '1rem',
        padding: '0.5rem 0.75rem',
        background: 'rgba(15, 19, 26, 0.85)',
        color: '#cdd5e0',
        borderRadius: '0.5rem',
        fontSize: '0.85rem',
        fontFamily: 'ui-monospace, SFMono-Regular, monospace',
        pointerEvents: 'none',
      }}
    >
      {activeAgentName && <div>agent: {activeAgentName}</div>}
      {currentStage && <div>stage: {currentStage}</div>}
    </div>
  )
}
