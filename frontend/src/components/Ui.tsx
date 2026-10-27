import { createContext, forwardRef, useContext, useEffect, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { signOut } from '../auth'

type Theme = 'light' | 'dark'
type ThemePreference = Theme | 'system'
type ThemeContextValue = { theme: Theme; preference: ThemePreference; toggle: () => void; useSystem: () => void }
const ThemeContext = createContext<ThemeContextValue>({ theme: 'light', preference: 'system', toggle: () => {}, useSystem: () => {} })

function getThemePreference(): ThemePreference {
  try {
    const saved = window.localStorage.getItem('zipp-theme')
    return saved === 'light' || saved === 'dark' ? saved : 'system'
  } catch { return 'system' }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreference] = useState<ThemePreference>(getThemePreference)
  const [systemTheme, setSystemTheme] = useState<Theme>(() => window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  const theme = preference === 'system' ? systemTheme : preference

  useEffect(() => {
    const query = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!query) return
    const onChange = (event: MediaQueryListEvent) => setSystemTheme(event.matches ? 'dark' : 'light')
    query.addEventListener?.('change', onChange)
    return () => query.removeEventListener?.('change', onChange)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme
    root.style.colorScheme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0b0f0e' : '#f5f7f9')
  }, [theme])

  useEffect(() => {
    try {
      if (preference === 'system') window.localStorage.removeItem('zipp-theme')
      else window.localStorage.setItem('zipp-theme', preference)
    } catch { /* Theme preference remains available for this session. */ }
  }, [preference])

  const toggle = () => setPreference(theme === 'dark' ? 'light' : 'dark')
  const useSystem = () => setPreference('system')
  return <ThemeContext.Provider value={{ theme, preference, toggle, useSystem }}>{children}</ThemeContext.Provider>
}

export function ThemeToggle() {
  const { theme, preference, toggle, useSystem } = useContext(ThemeContext)
  const target = theme === 'dark' ? 'light' : 'dark'
  return <div className="theme-controls">
    <button className={`theme-toggle theme-${theme}`} type="button" aria-label={`Switch to ${target} mode`} aria-pressed={theme === 'dark'} title={preference === 'system' ? `Following browser preference: ${theme} mode` : `Using ${theme} mode`} onClick={toggle}>
      <svg viewBox="0 0 24 24" aria-hidden="true">{theme === 'dark' ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" /></> : <path d="M20.2 15.2A8.5 8.5 0 0 1 8.8 3.8 8.5 8.5 0 1 0 20.2 15.2Z" />}</svg>
      <span>{theme === 'dark' ? 'Dark' : 'Light'}</span><span className="theme-switch" aria-hidden="true"><span /></span>
    </button>
    {preference !== 'system' && <button className="theme-auto" type="button" onClick={useSystem}>Use system</button>}
  </div>
}

export function DotGridBackground({ children }: { children: ReactNode }) {
  return <div className="app-shell">{children}</div>
}

export function WorkspaceLayout({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <div className="workspace">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="sidebar">
      <Link className="brand-mark" to="/links" aria-label="Zipp home">zipp<span className="cursor">.</span></Link>
      <div className="workspace-label">WORKSPACE</div>
      <nav aria-label="Main navigation">
        <NavLink to="/links" end className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}><span className="nav-icon" aria-hidden="true">↗</span> Links</NavLink>
      </nav>
      <div className="sidebar-bottom"><span className="avatar" aria-hidden="true">Z</span><div className="account-copy"><strong>Your workspace</strong><small>Personal account</small></div><button className="signout-button" onClick={() => void signOut()} aria-label="Sign out">↗</button></div>
    </aside>
    <div className="workspace-main">
      <header className="workspace-header"><div><p className="eyebrow">LINK MANAGEMENT</p><h1>{title}</h1><p className="page-description">{description}</p></div><div className="header-actions"><ThemeToggle /><button className="mobile-signout" onClick={() => void signOut()}>Sign out</button></div></header>
      <main id="main-content" className="workspace-content">{children}</main>
    </div>
  </div>
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>
}

export const Button = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { kind?: 'primary' | 'ghost' | 'danger' }>(function Button({ kind = 'primary', children, ...props }, ref) {
  return <button ref={ref} className={`button button-${kind}`} {...props}>{children}</button>
})

export function Input({ label, id, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; id: string }) {
  return <label className="field" htmlFor={id}><span>{label}</span><input id={id} {...props} /></label>
}

export function Badge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}

const frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
export function BrailleSpinner() {
  const [frame, setFrame] = useState(0)
  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const timer = window.setInterval(() => setFrame(value => (value + 1) % frames.length), 90)
    return () => window.clearInterval(timer)
  }, [])
  return <span role="status" aria-label="Loading">{frames[frame]}</span>
}

export function StepProgress({ step }: { step: number }) {
  return <div className="step-progress" role="progressbar" aria-valuenow={step} aria-valuemin={0} aria-valuemax={4} aria-label="Sign-in progress">{[0, 1, 2, 3].map(index => <span className={index < step ? 'filled' : ''} key={index} />)}</div>
}

export function StatusLine({ error, success }: { error?: string | null; success?: string | null }) {
  if (!error && !success) return null
  return <p className={`status-line ${error ? 'status-error' : 'status-success'}`} role={error ? 'alert' : 'status'}>{error || success}</p>
}

export function ConfirmPanel({ title, body, onCancel, onConfirm, pending }: { title: string; body: string; onCancel: () => void; onConfirm: () => void; pending: boolean }) {
  const cancelRef = useRef<HTMLButtonElement>(null)
  useEffect(() => { cancelRef.current?.focus() }, [])
  return <section className="confirm-panel" role="group" aria-label={title} onKeyDown={event => { if (event.key === 'Escape') onCancel() }}>
    <h2>{title}</h2><p>{body}</p>
    <div className="confirm-actions"><Button ref={cancelRef} kind="ghost" onClick={onCancel} disabled={pending}>cancel</Button><Button kind="danger" onClick={onConfirm} disabled={pending}>{pending ? <BrailleSpinner /> : 'yes, disable'}</Button></div>
  </section>
}
