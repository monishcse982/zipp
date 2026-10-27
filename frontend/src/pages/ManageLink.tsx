import { useRef, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, type ManagedLink } from '../api'
import { signIn } from '../auth'
import { useAuth } from '../AuthContext'
import { AppLayout, Badge, BrailleSpinner, Button, ConfirmPanel, Input, Panel, StatusLine } from '../components/Ui'
import { isHttpUrl } from './Links'

export function ManageLink() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [destination, setDestination] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const disableButton = useRef<HTMLButtonElement>(null)
  const backLink = useRef<HTMLAnchorElement>(null)
  const path = `/links/${encodeURIComponent(id)}`
  const link = useQuery({ queryKey: ['link', id], queryFn: () => api<ManagedLink>(user!, path), enabled: !!user })
  const save = useMutation({ mutationFn: (url: string) => api<ManagedLink>(user!, path, { method: 'PATCH', body: JSON.stringify({ url }) }), onSuccess: () => { setSuccess('Destination saved'); void queryClient.invalidateQueries({ queryKey: ['link', id] }); void queryClient.invalidateQueries({ queryKey: ['links'] }) } })
  const disable = useMutation({ mutationFn: () => api<void>(user!, path, { method: 'DELETE' }), onSuccess: () => { setConfirm(false); setSuccess('Link disabled'); void queryClient.invalidateQueries({ queryKey: ['link', id] }); void queryClient.invalidateQueries({ queryKey: ['links'] }); requestAnimationFrame(() => backLink.current?.focus()) } })
  function cancelDisable() { setConfirm(false); requestAnimationFrame(() => disableButton.current?.focus()) }
  function submit(event: FormEvent) {
    event.preventDefault(); setError(null); setSuccess(null)
    const url = destination ?? link.data?.original_url ?? ''
    if (!isHttpUrl(url)) { setError('Enter an http:// or https:// URL'); return }
    save.mutate(url)
  }
  if (link.isPending) return <AppLayout title="Link details" description="Loading link details."><Panel><BrailleSpinner /> Loading link</Panel></AppLayout>
  if (link.error) {
    const message = link.error instanceof ApiError ? ({ 401: 'Session expired.', 403: 'You cannot manage this link.', 404: 'Link not found.' } as Record<number, string>)[link.error.status] || link.error.message : link.error.message
    return <AppLayout title="Link details" description="Manage your short link."><Link className="back-link" to="/links">← All links</Link><Panel><StatusLine error={message} />{link.error instanceof ApiError && link.error.status === 401 && <Button onClick={() => void signIn(path)}>Sign in</Button>}</Panel></AppLayout>
  }
  const item = link.data
  const currentDestination = destination ?? item.original_url
  return <AppLayout title="Link details" description="Review performance and update your destination.">
    <Link ref={backLink} className="back-link" to="/links">← All links</Link>
    <Panel className="detail-hero"><div><p className="eyebrow">SHORT LINK</p><h2 className="manage-title">{item.shortened_url}</h2>{item.title && <p className="detail-title">{item.title}</p>}</div><Badge status={item.status} /></Panel>
    <Panel className="details-panel"><div className="panel-heading"><div><p className="eyebrow">AT A GLANCE</p><h2>Link details</h2></div></div><dl><div><dt>Created</dt><dd>{new Date(item.created_at).toLocaleDateString()}</dd></div><div><dt>Status</dt><dd><Badge status={item.status} /></dd></div><div><dt>Expires</dt><dd>{item.expires_at ? new Date(item.expires_at).toLocaleDateString() : 'Never'}</dd></div><div><dt>Total visits</dt><dd>{item.visit_count}{item.max_visits !== null ? ` / ${item.max_visits}` : ''}</dd></div><div><dt>Access</dt><dd>{item.policy_type.replace('_', ' ')}</dd></div></dl></Panel>
    {item.status === 'active' && <Panel className="edit-panel"><div className="panel-heading"><div><p className="eyebrow">DESTINATION</p><h2>Update destination</h2></div></div><form className="edit-form" onSubmit={submit}><Input id="destination" label="Destination URL" type="url" value={currentDestination} onChange={event => setDestination(event.target.value)} required /><Button type="submit" disabled={save.isPending}>{save.isPending ? <BrailleSpinner /> : 'Save changes'}</Button></form></Panel>}
    <StatusLine error={error || save.error?.message || disable.error?.message} success={success} />
    {item.status === 'active' && (confirm ? <ConfirmPanel title={`disable ${item.shortened_url}?`} body="Visitors will no longer be redirected. This cannot be undone." onCancel={cancelDisable} onConfirm={() => disable.mutate()} pending={disable.isPending} /> : <Button ref={disableButton} kind="danger" onClick={() => setConfirm(true)}>disable link</Button>)}
  </AppLayout>
}
