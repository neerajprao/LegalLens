import type { ReactNode } from 'react'
import { colors, mutedStyle, panelIconStyle, panelTitleRowStyle } from './shared'

export function PanelHeader({
  icon,
  title,
  subtitle,
  action,
}: {
  icon: string
  title: string
  subtitle?: string
  action?: ReactNode
}) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
      <div>
        <div style={panelTitleRowStyle}>
          <span style={panelIconStyle}>{icon}</span>
          <h2 style={{ color: colors.text }}>{title}</h2>
        </div>
        {subtitle && <p style={{ ...mutedStyle, marginTop: '0.3rem', maxWidth: 560 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
