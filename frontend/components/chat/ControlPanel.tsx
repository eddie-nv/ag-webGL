'use client'

import { useState } from 'react'

import type { Control, ControlPanelPayload, EmitSpec } from '@shared/schema/sceneSchema'
import { routeSceneEvent } from '@/hooks/useSceneActions'
import { sceneLog } from '@/lib/debug'
import type { SceneSetup } from '@/lib/sceneSetup'

interface Props {
  panel: ControlPanelPayload
  setup: SceneSetup
}

export function ControlPanel({ panel, setup }: Props) {
  return (
    <div style={panelStyle}>
      <div style={panelTitleStyle}>{panel.title ?? 'controls'}</div>
      <div style={panelControlsStyle}>
        {panel.controls.map((c, i) => (
          <ControlEntry key={`${c.kind}-${i}-${c.label}`} control={c} setup={setup} />
        ))}
      </div>
    </div>
  )
}

function ControlEntry({ control, setup }: { control: Control; setup: SceneSetup }) {
  if (control.kind === 'button') return <ButtonEntry control={control} setup={setup} />
  return <ToggleEntry control={control} setup={setup} />
}

function ButtonEntry({
  control,
  setup,
}: {
  control: Extract<Control, { kind: 'button' }>
  setup: SceneSetup
}) {
  const onClick = () => {
    sceneLog('control button:', control.label)
    dispatchEmits(control.emits, setup)
  }
  return (
    <button type="button" onClick={onClick} style={buttonStyle(false)}>
      {control.label}
    </button>
  )
}

function ToggleEntry({
  control,
  setup,
}: {
  control: Extract<Control, { kind: 'toggle' }>
  setup: SceneSetup
}) {
  const [on, setOn] = useState<boolean>(control.default ?? false)
  const onClick = () => {
    const next = !on
    sceneLog('control toggle:', control.label, '->', next)
    dispatchEmits(next ? control.on : control.off, setup)
    setOn(next)
  }
  return (
    <button type="button" onClick={onClick} style={buttonStyle(on)}>
      <span style={toggleDot(on)} aria-hidden />
      {control.label}
    </button>
  )
}

function dispatchEmits(emits: EmitSpec[], setup: SceneSetup): void {
  for (const e of emits) {
    routeSceneEvent(
      { name: e.name, value: e.value },
      { controller: setup.controller },
    )
  }
}

const panelStyle: React.CSSProperties = {
  padding: '0.5rem 0.75rem',
  background: '#161b25',
  borderRadius: '0.5rem',
  border: '1px solid #1f2530',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.5rem',
}

const panelTitleStyle: React.CSSProperties = {
  fontSize: '0.7rem',
  color: '#697080',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
}

const panelControlsStyle: React.CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.4rem',
}

function buttonStyle(active: boolean): React.CSSProperties {
  return {
    padding: '0.4rem 0.7rem',
    background: active ? '#3a8a4a' : '#1d2533',
    color: active ? 'white' : '#cdd5e0',
    border: `1px solid ${active ? '#4ca85e' : '#2a3242'}`,
    borderRadius: '0.35rem',
    cursor: 'pointer',
    fontSize: '0.8rem',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    fontFamily: 'inherit',
  }
}

function toggleDot(on: boolean): React.CSSProperties {
  return {
    display: 'inline-block',
    width: '0.5rem',
    height: '0.5rem',
    borderRadius: '50%',
    background: on ? '#a3d680' : '#3a4252',
  }
}
