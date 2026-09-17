import type { CSSProperties } from 'react'

// ---------------------------------------------------------------------------
// Legal Lens design system — a single shared set of tokens/helpers so every
// panel renders as one coherent, premium dark-themed product rather than a
// pile of ad hoc inline styles. CLAUDE.md Phase 8 scoped the tab-flow as an
// information-architecture pass, not a visual design pass — this closes that
// visual gap.
// ---------------------------------------------------------------------------

// Cyan is the platform's primary accent (kept under the historical "gold*" key
// names so every consuming panel — all of which pre-date this palette swap —
// repaints automatically without a per-file rename).
export const colors = {
  bg: '#121519',
  surface: '#1a1f25',
  surface2: '#222931',
  border: '#2a3037',
  borderSoft: '#232830',
  text: '#eaedf0',
  textDim: '#b7bcc2',
  textFaint: '#7e8790',
  gold: '#0cbde8',
  goldBright: '#4dd3f0',
  goldSoft: 'rgba(12, 189, 232, 0.12)',
  goldBorder: 'rgba(12, 189, 232, 0.35)',
  danger: '#e35d5d',
  dangerSoft: 'rgba(227, 93, 93, 0.12)',
  warn: '#e5b52f',
  warnSoft: 'rgba(229, 181, 47, 0.1)',
  ok: '#42c98a',
  okSoft: 'rgba(66, 201, 138, 0.12)',
}

export const mono = "'IBM Plex Mono', ui-monospace, 'SFMono-Regular', Consolas, monospace"

// Uppercase monospace "SOURCE // VALUE" style label, used for case IDs,
// evidence IDs, chunk references, and other technical metadata.
export const monoLabelStyle: CSSProperties = {
  fontFamily: mono,
  fontSize: '0.68rem',
  fontWeight: 500,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: colors.textFaint,
}

// Small glyph prefix for status text — never the sole signal (text label
// always accompanies it), just a fast-scan visual anchor.
export const statusDot: Record<string, string> = {
  supported: '●',
  verified: '●',
  active: '●',
  high: '●',
  partially_supported: '◐',
  medium: '◐',
  unsupported: '○',
  pending: '○',
  low: '○',
  disputed: '×',
  none: '!',
  warning: '!',
}

export const severityColor: Record<string, string> = {
  strong: colors.danger,
  moderate: colors.warn,
  weak: colors.textFaint,
  unspecified: colors.textFaint,
}

export const severityBg: Record<string, string> = {
  strong: colors.dangerSoft,
  moderate: colors.warnSoft,
  weak: 'rgba(255,255,255,0.04)',
  unspecified: 'rgba(255,255,255,0.04)',
}

export const statusColor: Record<string, string> = {
  supported: colors.ok,
  partially_supported: colors.warn,
  unsupported: colors.danger,
  disputed: colors.danger,
}

export const statusBg: Record<string, string> = {
  supported: colors.okSoft,
  partially_supported: colors.warnSoft,
  unsupported: colors.dangerSoft,
  disputed: colors.dangerSoft,
}

// ---- structure -------------------------------------------------------------

export const panelStyle: CSSProperties = {
  backgroundColor: colors.surface,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  padding: '1.5rem 1.6rem',
  marginTop: '1.25rem',
  boxShadow: '0 8px 24px -18px rgba(0,0,0,0.6)',
}

export const cardStyle: CSSProperties = {
  background: colors.surface2,
  border: `1px solid ${colors.borderSoft}`,
  borderRadius: 6,
  padding: '0.9rem 1rem',
  marginTop: '0.6rem',
}

export const dividerStyle: CSSProperties = {
  border: 'none',
  borderTop: `1px solid ${colors.borderSoft}`,
  margin: '0.9rem 0',
}

export function panelHeader(icon: string, title: string): { icon: string; title: string } {
  return { icon, title }
}

// ---- typography helpers -----------------------------------------------------

export const eyebrowStyle: CSSProperties = {
  textTransform: 'uppercase',
  letterSpacing: '0.12em',
  fontSize: '0.72rem',
  fontWeight: 500,
  fontFamily: mono,
  color: colors.textFaint,
}

export const mutedStyle: CSSProperties = {
  fontSize: '0.86rem',
  color: colors.textFaint,
}

export const emptyStateStyle: CSSProperties = {
  fontSize: '0.88rem',
  color: colors.textFaint,
  fontStyle: 'italic',
  listStyle: 'none',
  paddingLeft: 0,
}

// ---- form controls -----------------------------------------------------

export const inputStyle: CSSProperties = {
  background: colors.bg,
  border: `1px solid ${colors.border}`,
  borderRadius: 6,
  padding: '0.55rem 0.75rem',
  color: colors.text,
  fontSize: '0.92rem',
  outline: 'none',
}

export const textareaStyle: CSSProperties = {
  ...inputStyle,
  width: '100%',
  resize: 'vertical',
  lineHeight: 1.55,
}

export const selectStyle: CSSProperties = {
  ...inputStyle,
  cursor: 'pointer',
}

export const fieldRowStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '0.55rem',
  alignItems: 'center',
}

// ---- buttons -----------------------------------------------------

export const buttonStyle: CSSProperties = {
  padding: '0.55rem 1.05rem',
  cursor: 'pointer',
  borderRadius: 6,
  border: `1px solid ${colors.gold}`,
  background: colors.gold,
  color: '#0a1216',
  fontWeight: 600,
  fontSize: '0.86rem',
  letterSpacing: '0.01em',
  transition: 'transform 0.12s ease, box-shadow 0.12s ease, opacity 0.12s ease',
  boxShadow: '0 0 0 1px rgba(12,189,232,0.15), 0 8px 20px -12px rgba(12, 189, 232, 0.5)',
}

export const secondaryButtonStyle: CSSProperties = {
  padding: '0.55rem 1.05rem',
  cursor: 'pointer',
  borderRadius: 6,
  border: `1px solid ${colors.border}`,
  background: 'transparent',
  color: colors.text,
  fontWeight: 600,
  fontSize: '0.86rem',
  transition: 'border-color 0.12s ease, background 0.12s ease',
}

export const ghostButtonStyle: CSSProperties = {
  padding: '0.32rem 0.65rem',
  cursor: 'pointer',
  borderRadius: 5,
  border: `1px solid ${colors.border}`,
  background: 'transparent',
  color: colors.textDim,
  fontWeight: 500,
  fontSize: '0.78rem',
}

export const dangerGhostButtonStyle: CSSProperties = {
  ...ghostButtonStyle,
  color: colors.danger,
  borderColor: 'rgba(226, 104, 90, 0.35)',
}

export function disabledStyle(disabled: boolean): CSSProperties {
  return disabled ? { opacity: 0.45, cursor: 'not-allowed', boxShadow: 'none', transform: 'none' } : {}
}

// ---- badges / chips -----------------------------------------------------

export function badgeStyle(color: string, bg: string): CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.3rem',
    padding: '0.14rem 0.5rem',
    borderRadius: 4,
    fontSize: '0.68rem',
    fontFamily: mono,
    fontWeight: 500,
    letterSpacing: '0.08em',
    color,
    background: bg,
    border: `1px solid ${color}33`,
    textTransform: 'uppercase',
  }
}

export const tagStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0.14rem 0.55rem',
  borderRadius: 4,
  fontSize: '0.72rem',
  fontFamily: mono,
  letterSpacing: '0.04em',
  color: colors.textDim,
  background: 'rgba(255,255,255,0.04)',
  border: `1px solid ${colors.border}`,
}

export const calloutStyle: Record<'info' | 'warn' | 'danger' | 'ok', CSSProperties> = {
  info: {
    background: colors.goldSoft,
    border: `1px solid ${colors.goldBorder}`,
    borderRadius: 6,
    padding: '0.75rem 0.95rem',
    fontSize: '0.86rem',
    color: colors.text,
  },
  warn: {
    background: colors.warnSoft,
    border: `1px solid ${colors.warn}59`,
    borderRadius: 6,
    padding: '0.75rem 0.95rem',
    fontSize: '0.86rem',
    color: colors.text,
  },
  danger: {
    background: colors.dangerSoft,
    border: `1px solid ${colors.danger}59`,
    borderRadius: 6,
    padding: '0.75rem 0.95rem',
    fontSize: '0.86rem',
    color: colors.text,
  },
  ok: {
    background: colors.okSoft,
    border: `1px solid ${colors.ok}59`,
    borderRadius: 6,
    padding: '0.75rem 0.95rem',
    fontSize: '0.86rem',
    color: colors.text,
  },
}

// ---- tabs -----------------------------------------------------

export const tabBarStyle: CSSProperties = {
  display: 'flex',
  gap: '0.4rem',
  borderBottom: `1px solid ${colors.border}`,
  marginTop: '1.75rem',
  paddingBottom: 0,
}

export function tabButtonStyle(active: boolean, enabled = true): CSSProperties {
  return {
    padding: '0.7rem 1.1rem',
    cursor: enabled ? 'pointer' : 'not-allowed',
    border: 'none',
    borderBottom: active ? `2px solid ${colors.gold}` : '2px solid transparent',
    marginBottom: '-1px',
    background: 'transparent',
    fontFamily: mono,
    fontWeight: 500,
    fontSize: '0.74rem',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    color: active ? colors.goldBright : enabled ? colors.textDim : colors.textFaint,
    opacity: enabled ? 1 : 0.5,
    transition: 'color 0.15s ease, border-color 0.15s ease',
  }
}

// ---- panel section title with icon -----------------------------------------------------

export const panelTitleRowStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '0.6rem',
  marginBottom: '0.2rem',
}

export const panelIconStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 30,
  height: 30,
  borderRadius: 6,
  background: colors.goldSoft,
  border: `1px solid ${colors.goldBorder}`,
  fontSize: '0.95rem',
  flexShrink: 0,
}
