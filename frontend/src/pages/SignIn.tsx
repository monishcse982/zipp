import { lazy, Suspense, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { signIn } from '../auth'
import { useAuth } from '../AuthContext'
import { BrailleSpinner, Button, StatusLine, StepProgress } from '../components/Ui'

const DotOrb = lazy(() => import('../components/DotOrb'))

export function SignIn() {
  const { user, loading, error: authError } = useAuth()
  const location = useLocation()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const from = (location.state as { from?: string } | null)?.from || '/links'
  if (loading) return <div className="auth-page auth-state"><Suspense fallback={null}><DotOrb /></Suspense><p>Restoring your session <BrailleSpinner /></p></div>
  if (user) return <Navigate to={from} replace />
  async function start() {
    setBusy(true)
    setError(null)
    try { await signIn(from) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start sign in'); setBusy(false) }
  }
  return <main className="auth-page">
    <header className="auth-top"><span className="brand-mark">zipp<span className="cursor">.</span></span><span className="secure-label"><span aria-hidden="true">●</span> Secure link management</span></header>
    <div className="auth-layout"><section className="auth-story"><div className="auth-story-copy"><p className="eyebrow">A LITTLE LESS URL</p><h1>Make every<br />link <span>count.</span></h1><p>Short links with the control and clarity you need to share with confidence.</p><div className="auth-benefits"><span><b>01</b> Create clean short links</span><span><b>02</b> Set access and expiry rules</span><span><b>03</b> Keep track of every link</span></div></div><Suspense fallback={null}><DotOrb /></Suspense></section>
    <section className="auth-card"><p className="eyebrow">WELCOME TO ZIPP</p><h2>Sign in to continue</h2><p className="auth-card-copy">Your links are waiting for you.</p><StatusLine error={error || authError} /><Button onClick={start} disabled={busy}>{busy ? <>Connecting <BrailleSpinner /></> : 'Continue with secure sign in'}</Button>{busy && <StepProgress step={2} />}<small>Sign in opens our secure hosted login.</small></section></div>
    <footer className="auth-footer"><span>zipp<span className="cursor">.</span></span><span>Short links. Full control.</span></footer>
  </main>
}
