import { useCoAgent, useCopilotChat } from '@copilotkit/react-core'

export interface UseSceneAgentReturn {
  currentStage: string | null
  activeAgentName: string | null
  sendMessage: (text: string) => void
}

interface SceneAgentState {
  currentStage?: string
  activeAgentName?: string
}

/**
 * Thin wrapper around CopilotKit's useCoAgent + useCopilotChat that exposes
 * scene-pipeline specific fields (currentStage, activeAgentName, sendMessage).
 * Stage / agent tracking is best-effort -- the underlying agent state shape
 * is set by the Python pipeline and read optionally here.
 */
export function useSceneAgent(name = 'sceneAgent'): UseSceneAgentReturn {
  const { state } = useCoAgent<SceneAgentState>({ name })
  const { appendMessage } = useCopilotChat() as unknown as {
    appendMessage?: (msg: { role: string; content: string }) => void
  }

  return {
    currentStage: state?.currentStage ?? null,
    activeAgentName: state?.activeAgentName ?? null,
    sendMessage: (text: string) => {
      appendMessage?.({ role: 'user', content: text })
    },
  }
}
