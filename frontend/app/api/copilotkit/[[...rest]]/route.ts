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

// Optional catch-all so /api/copilotkit AND /api/copilotkit/threads (and any
// other subpath CopilotKit's runtime serves) all funnel through handleRequest.
export const GET = handler.handleRequest
export const POST = handler.handleRequest
