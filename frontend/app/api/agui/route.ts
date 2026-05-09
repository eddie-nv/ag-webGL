/**
 * Same-origin proxy from the browser to the Python /agui SSE endpoint.
 * The browser POSTs JSON here; we forward to SCENE_AGENT_URL and pipe the
 * text/event-stream body straight back. No CopilotKit, no GraphQL -- just
 * a passthrough so the canvas can subscribe to AG-UI events directly.
 *
 * `dynamic = force-dynamic` and the explicit nodejs runtime stop Next.js
 * App Router from buffering the upstream body waiting for a complete
 * response -- without these, the stream is held until the backend closes
 * even though we yield SSE chunks incrementally on the Python side.
 */

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const BACKEND_URL = process.env.SCENE_AGENT_URL ?? 'http://localhost:8000/agui'

export async function POST(req: Request): Promise<Response> {
  const body = await req.text()
  let upstream: Response
  try {
    upstream = await fetch(BACKEND_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
    })
  } catch (err) {
    return new Response(
      `Failed to reach backend at ${BACKEND_URL}: ${(err as Error).message}`,
      { status: 502 },
    )
  }

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => '')
    return new Response(`Upstream ${upstream.status}: ${text}`, {
      status: upstream.status || 502,
    })
  }

  return new Response(upstream.body, {
    headers: {
      'content-type': 'text/event-stream',
      'cache-control': 'no-cache, no-transform',
      connection: 'keep-alive',
    },
  })
}
