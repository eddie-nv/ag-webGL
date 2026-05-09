import { HttpAgent } from '@ag-ui/client'
import { CopilotRuntime, copilotRuntimeNextJSAppRouterEndpoint } from '@copilotkit/runtime'

const AGENT_URL = process.env.SCENE_AGENT_URL ?? 'http://localhost:8000/agui'

const sceneAgent = new HttpAgent({ url: AGENT_URL })

const runtime = new CopilotRuntime({
  agents: { sceneAgent },
})

const handler = copilotRuntimeNextJSAppRouterEndpoint({
  runtime,
  endpoint: '/api/copilotkit',
})

export const POST = handler.handleRequest
