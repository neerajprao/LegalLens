import type { CSSProperties } from 'react'

export const panelStyle: CSSProperties = {
  border: '1px solid #ddd',
  borderRadius: 8,
  padding: '1rem',
  marginTop: '1rem',
}

export const buttonStyle: CSSProperties = {
  padding: '0.4rem 0.8rem',
  cursor: 'pointer',
}

export const severityColor: Record<string, string> = {
  strong: '#c0392b',
  moderate: '#d68910',
  weak: '#7f8c8d',
  unspecified: '#7f8c8d',
}
