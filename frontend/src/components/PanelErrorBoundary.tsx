import { Component, type ErrorInfo, type ReactNode } from 'react'
import { calloutStyle, eyebrowStyle } from './shared'

interface Props {
  panelName: string
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Without this, a render-time exception in any one panel (e.g. a backend response missing a
 * field a panel assumed would always be present — a real risk with a local 7B model's JSON
 * output under the load of "Analyze the case" firing several agent calls) unmounts React's
 * *entire* tree, since no error boundary existed anywhere in the app: the whole page goes blank
 * instead of just that one panel. Scoped per-panel (one instance wraps one panel in App.tsx) so
 * a single bad response degrades one card, not the whole session — the rest of the case data
 * already fetched by other panels stays visible and usable.
 */
export class PanelErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[${this.props.panelName}] crashed while rendering:`, error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <section style={{ ...calloutStyle.danger, marginTop: '1.25rem' }}>
          <div style={{ ...eyebrowStyle, marginBottom: '0.3rem' }}>{this.props.panelName} failed to render</div>
          This panel hit an unexpected response shape and couldn't display its results. The rest of the page is
          unaffected — try re-running this panel, or reload the page if it keeps happening.
          <div style={{ fontSize: '0.75rem', marginTop: '0.5rem', opacity: 0.7 }}>{this.state.error.message}</div>
        </section>
      )
    }
    return this.props.children
  }
}
