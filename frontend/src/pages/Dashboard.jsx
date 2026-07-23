import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { apiGet, apiPost, apiDelete, apiUpload } from '../lib/api'
import TypePill from '../components/TypePill'
import CopyButton from '../components/CopyButton'
import {
  IconUpload, IconDatabase, IconKey, IconPlus, IconTrash, IconSpinner,
  IconArrowRight, IconSparkle, IconCheck,
} from '../components/icons'

export default function Dashboard() {
  const { user } = useAuth()
  const [me, setMe] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [meRes, ds, ks] = await Promise.all([
        apiGet('/api/account/me'),
        apiGet('/api/datasets'),
        apiGet('/api/keys'),
      ])
      setMe(meRes)
      setDatasets(ds)
      setKeys(ks)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const [notice, setNotice] = useState('')

  useEffect(() => { load() }, [load])

  // Handle the redirect back from Stripe Checkout.
  useEffect(() => {
    const status = new URLSearchParams(window.location.search).get('checkout')
    if (!status) return
    window.history.replaceState({}, '', '/dashboard')
    if (status !== 'success') return
    setNotice('Payment received — activating your Pro plan…')
    // The plan flips via a Stripe webhook, so poll a few times for it to land.
    let tries = 0
    const iv = setInterval(() => {
      tries += 1
      load()
      if (tries >= 5) clearInterval(iv)
    }, 1500)
    return () => clearInterval(iv)
  }, [load])

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        <IconSpinner width={28} height={28} />
      </div>
    )
  }

  return (
    <main className="container-page py-10">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-400">{user?.email}</p>
        </div>
        <PlanControl me={me} />
      </div>

      {notice && (
        <p className="mt-6 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{notice}</p>
      )}
      {error && (
        <p className="mt-6 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <UploadCard plan={me?.plan} datasetCount={datasets.length} onUploaded={load} />
          <DatasetsList datasets={datasets} onDeleted={load} />
        </div>
        <div className="space-y-6">
          <ApiKeys keys={keys} onChange={load} />
        </div>
      </div>
    </main>
  )
}

function PlanControl({ me }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const isPro = me?.plan === 'pro'

  // Both actions hand off to a Stripe-hosted page, so we just redirect to the returned URL.
  async function go(path) {
    setBusy(true)
    setErr('')
    try {
      const { url } = await apiPost(path)
      if (url) window.location.href = url
      else setErr('Could not start billing session.')
    } catch (e) {
      setErr(e.message)
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-3">
        <span className={`badge ${isPro ? 'border-brand-400/40 text-brand-200' : ''}`}>
          {isPro && <IconSparkle width={13} height={13} className="text-brand-400" />}
          {isPro ? 'Pro plan' : 'Free plan'}
        </span>
        {isPro ? (
          <button onClick={() => go('/api/billing/portal')} disabled={busy} className="btn-ghost">
            {busy ? <IconSpinner width={16} height={16} /> : 'Manage billing'}
          </button>
        ) : (
          <button onClick={() => go('/api/billing/checkout')} disabled={busy} className="btn-primary">
            {busy ? <IconSpinner width={16} height={16} /> : <>Upgrade to Pro <IconArrowRight width={15} height={15} /></>}
          </button>
        )}
      </div>
      {err && <span className="text-xs text-red-300">{err}</span>}
    </div>
  )
}

function UploadCard({ plan, datasetCount, onUploaded }) {
  const inputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const atFreeCap = plan === 'free' && datasetCount >= 1

  async function handleFile(file) {
    if (!file) return
    setError('')
    setResult(null)
    setUploading(true)
    try {
      const ds = await apiUpload('/api/datasets', file)
      setResult(ds)
      await onUploaded()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragOver(false)
    if (atFreeCap) return
    handleFile(e.dataTransfer.files?.[0])
  }

  return (
    <section className="card p-6">
      <div className="flex items-center gap-2">
        <IconUpload width={18} height={18} className="text-brand-400" />
        <h2 className="font-semibold text-white">Upload a spreadsheet</h2>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => !atFreeCap && inputRef.current?.click()}
        className={`mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-12 text-center transition
          ${dragOver ? 'border-brand-400/60 bg-brand-500/5' : 'border-white/10 hover:border-white/25'}
          ${atFreeCap ? 'cursor-not-allowed opacity-50' : ''}`}
      >
        <input ref={inputRef} type="file" accept=".csv,text/csv" hidden
          onChange={(e) => handleFile(e.target.files?.[0])} />
        {uploading ? (
          <IconSpinner width={28} height={28} className="text-brand-400" />
        ) : (
          <span className="flex h-14 w-14 items-center justify-center rounded-xl bg-brand-500/10 text-brand-400">
            <IconUpload width={24} height={24} />
          </span>
        )}
        <p className="mt-4 text-sm font-medium text-slate-200">
          {uploading ? 'Inferring schema…' : 'Drop a CSV here or click to browse'}
        </p>
        <p className="mt-1 text-xs text-slate-500">We'll detect each column's type automatically.</p>
      </div>

      {atFreeCap && (
        <p className="mt-3 text-xs text-amber-300/80">
          Free plan is limited to 1 dataset. Upgrade to Pro for unlimited uploads.
        </p>
      )}
      {error && <p className="mt-3 text-sm text-red-300">{error}</p>}

      {result && (
        <div className="mt-5 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.06] p-4">
          <div className="flex items-center gap-2 text-sm font-medium text-emerald-300">
            <IconCheck width={16} height={16} /> Detected schema for “{result.name}” · {result.row_count} rows
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {result.columns.map((c) => (
              <span key={c.name} className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs text-slate-300">
                {c.name} <TypePill type={c.data_type} />
              </span>
            ))}
          </div>
          <Link to={`/datasets/${result.id}`} className="btn-ghost mt-4">
            View API docs <IconArrowRight width={15} height={15} />
          </Link>
        </div>
      )}
    </section>
  )
}

function DatasetsList({ datasets, onDeleted }) {
  if (datasets.length === 0) {
    return (
      <section className="card flex flex-col items-center justify-center p-10 text-center">
        <IconDatabase width={28} height={28} className="text-slate-600" />
        <p className="mt-3 text-sm text-slate-400">No datasets yet. Upload your first CSV above.</p>
      </section>
    )
  }
  return (
    <section className="space-y-3">
      <h2 className="px-1 text-sm font-semibold uppercase tracking-wider text-slate-500">Your datasets</h2>
      {datasets.map((d) => (
        <DatasetRow key={d.id} dataset={d} onDeleted={onDeleted} />
      ))}
    </section>
  )
}

function DatasetRow({ dataset, onDeleted }) {
  const [busy, setBusy] = useState(false)
  async function remove(e) {
    e.preventDefault()
    if (!confirm(`Delete “${dataset.name}”? This removes its API and all rows.`)) return
    setBusy(true)
    try { await apiDelete(`/api/datasets/${dataset.id}`); await onDeleted() }
    finally { setBusy(false) }
  }
  return (
    <Link to={`/datasets/${dataset.id}`} className="card card-hover flex items-center justify-between p-5">
      <div className="flex items-center gap-4">
        <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-brand-400">
          <IconDatabase width={20} height={20} />
        </span>
        <div>
          <p className="font-semibold text-white">{dataset.name}</p>
          <p className="text-xs text-slate-500">{dataset.row_count} rows</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="hidden text-sm text-brand-400 sm:inline">View docs</span>
        <IconArrowRight width={16} height={16} className="text-slate-500" />
        <button onClick={remove} disabled={busy}
          className="ml-2 rounded-lg border border-white/10 p-2 text-slate-500 transition hover:border-red-500/40 hover:text-red-300">
          {busy ? <IconSpinner width={15} height={15} /> : <IconTrash width={15} height={15} />}
        </button>
      </div>
    </Link>
  )
}

function ApiKeys({ keys, onChange }) {
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState(null)

  async function create() {
    setCreating(true)
    try {
      const k = await apiPost('/api/keys')
      setNewKey(k.key)
      await onChange()
    } finally {
      setCreating(false)
    }
  }

  async function revoke(id) {
    if (!confirm('Revoke this key? Apps using it will stop working.')) return
    await apiDelete(`/api/keys/${id}`)
    await onChange()
  }

  return (
    <section className="card p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconKey width={18} height={18} className="text-brand-400" />
          <h2 className="font-semibold text-white">API keys</h2>
        </div>
        <button onClick={create} disabled={creating} className="btn-ghost">
          {creating ? <IconSpinner width={15} height={15} /> : <><IconPlus width={15} height={15} /> New</>}
        </button>
      </div>

      {newKey && (
        <div className="mt-4 rounded-xl border border-brand-400/30 bg-brand-500/[0.08] p-4">
          <p className="text-xs font-medium text-brand-200">Copy your key now — it won't be shown again.</p>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg bg-black/40 px-3 py-2 font-mono text-xs text-slate-200">{newKey}</code>
            <CopyButton text={newKey} />
          </div>
        </div>
      )}

      <div className="mt-4 space-y-2">
        {keys.length === 0 && <p className="text-sm text-slate-500">No keys yet. Create one to call your API.</p>}
        {keys.map((k) => (
          <div key={k.id} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5">
            <div>
              <code className="font-mono text-sm text-slate-200">{k.key_prefix}••••</code>
              <p className="text-[11px] text-slate-500">
                {k.last_used_at ? `Last used ${new Date(k.last_used_at).toLocaleDateString()}` : 'Never used'}
              </p>
            </div>
            <button onClick={() => revoke(k.id)}
              className="rounded-lg border border-white/10 p-2 text-slate-500 transition hover:border-red-500/40 hover:text-red-300">
              <IconTrash width={15} height={15} />
            </button>
          </div>
        ))}
      </div>
    </section>
  )
}
