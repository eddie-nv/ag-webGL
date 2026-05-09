'use client'

import { useEffect, useRef, useState } from 'react'

import { routeSceneEvent } from '@/hooks/useSceneActions'
import { sceneLog, sceneWarn } from '@/lib/debug'
import type { SceneSetup } from '@/lib/sceneSetup'

interface Props {
  setup: SceneSetup
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

interface AGUIEvent {
  type: string
  name?: string
  value?: unknown
  delta?: string
  messageId?: string
  role?: string
}

function localId(): string {
  // crypto.randomUUID exists in modern browsers; fall back if absent.
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `local-${Math.random().toString(36).slice(2)}-${Date.now()}`
}

export function SceneChat({ setup }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (): Promise<void> => {
    const prompt = input.trim()
    if (!prompt || streaming) return
    setInput('')
    setStreaming(true)
    setMessages((m) => [...m, { id: localId(), role: 'user', content: prompt }])

    try {
      await streamPipeline(prompt, (event) => handleEvent(event, setup, setMessages))
    } catch (err) {
      sceneWarn('chat failed:', err)
      setMessages((m) => [
        ...m,
        {
          id: localId(),
          role: 'assistant',
          content: `[error: ${(err as Error).message}]`,
        },
      ])
    } finally {
      setStreaming(false)
    }
  }

  return (
    <aside style={asideStyle}>
      <div style={headerStyle}>scene agent</div>
      <div style={listStyle}>
        {messages.length === 0 && (
          <div style={emptyHintStyle}>
            describe a process to animate, e.g.{' '}
            <em>walk me through a tomato plant&apos;s lifecycle</em>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} style={bubbleStyle(m.role)}>
            <div style={roleStyle}>{m.role}</div>
            <div>{m.content || '…'}</div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void send()
        }}
        style={formStyle}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="describe a process to animate..."
          disabled={streaming}
          style={inputStyle}
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          style={buttonStyle(streaming, input.trim().length > 0)}
        >
          {streaming ? '…' : 'send'}
        </button>
      </form>
    </aside>
  )
}

async function streamPipeline(
  prompt: string,
  onEvent: (e: AGUIEvent) => void,
): Promise<void> {
  const body = JSON.stringify({
    threadId: crypto.randomUUID(),
    runId: crypto.randomUUID(),
    messages: [{ role: 'user', content: prompt }],
  })
  const res = await fetch('/api/agui', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  })
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sep = buffer.indexOf('\n\n')
    while (sep !== -1) {
      const block = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      const dataLines = block
        .split('\n')
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trim())
      const json = dataLines.join('')
      if (json) {
        try {
          onEvent(JSON.parse(json) as AGUIEvent)
        } catch (e) {
          sceneWarn('SSE parse fail:', (e as Error).message, json.slice(0, 80))
        }
      }
      sep = buffer.indexOf('\n\n')
    }
  }
}

function handleEvent(
  event: AGUIEvent,
  setup: SceneSetup,
  setMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>,
): void {
  sceneLog('agui event:', event.type, event.name ?? event.messageId ?? '')

  // TEXT_MESSAGE_START -> push a fresh assistant bubble keyed by messageId.
  // The backend opens a new TextMessage per agent so each step gets its own
  // bubble in the chat (intro -> director -> layout -> ... -> done).
  if (event.type === 'TEXT_MESSAGE_START' && typeof event.messageId === 'string') {
    const id = event.messageId
    setMessages((m) => {
      if (m.some((msg) => msg.id === id)) return m
      return [...m, { id, role: 'assistant', content: '' }]
    })
    return
  }

  if (
    event.type === 'TEXT_MESSAGE_CONTENT' &&
    typeof event.messageId === 'string' &&
    typeof event.delta === 'string'
  ) {
    const id = event.messageId
    const delta = event.delta
    setMessages((m) => {
      const idx = m.findIndex((msg) => msg.id === id)
      if (idx === -1) {
        // No prior START event observed -- create the bubble now so we don't
        // drop content. Defensive; backend always sends START first.
        return [...m, { id, role: 'assistant', content: delta }]
      }
      const next = [...m]
      next[idx] = { ...next[idx], content: next[idx].content + delta }
      return next
    })
    return
  }

  if (
    event.type === 'CUSTOM' &&
    typeof event.name === 'string' &&
    event.name.startsWith('scene:')
  ) {
    routeSceneEvent(
      { name: event.name, value: event.value },
      { controller: setup.controller, camera: setup.camera },
    )
  }
}

const asideStyle: React.CSSProperties = {
  borderLeft: '1px solid #1f2530',
  background: '#10141c',
  display: 'flex',
  flexDirection: 'column',
  height: '100vh',
}

const headerStyle: React.CSSProperties = {
  padding: '0.5rem 1rem',
  borderBottom: '1px solid #1f2530',
  fontSize: '0.85rem',
  color: '#a0a8b8',
}

const listStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
  padding: '1rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.5rem',
}

const emptyHintStyle: React.CSSProperties = {
  color: '#697080',
  fontSize: '0.8rem',
  fontStyle: 'normal',
  padding: '0.5rem',
}

function bubbleStyle(role: 'user' | 'assistant'): React.CSSProperties {
  return {
    padding: '0.5rem 0.75rem',
    background: role === 'user' ? '#1d2533' : '#161b25',
    borderRadius: '0.5rem',
    fontSize: '0.85rem',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    border: '1px solid #1f2530',
  }
}

const roleStyle: React.CSSProperties = {
  fontSize: '0.7rem',
  color: '#697080',
  marginBottom: '0.25rem',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const formStyle: React.CSSProperties = {
  padding: '0.75rem',
  borderTop: '1px solid #1f2530',
  display: 'flex',
  gap: '0.5rem',
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: '0.5rem 0.75rem',
  background: '#1d2533',
  color: '#cdd5e0',
  border: '1px solid #2a3242',
  borderRadius: '0.4rem',
  fontSize: '0.85rem',
  outline: 'none',
}

function buttonStyle(streaming: boolean, hasInput: boolean): React.CSSProperties {
  const enabled = !streaming && hasInput
  return {
    padding: '0.5rem 1rem',
    background: enabled ? '#3a8a4a' : '#2a3242',
    color: 'white',
    border: 'none',
    borderRadius: '0.4rem',
    cursor: enabled ? 'pointer' : 'not-allowed',
    fontSize: '0.85rem',
    minWidth: '4rem',
  }
}
