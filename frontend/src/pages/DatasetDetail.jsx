import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiGet, API_URL } from '../lib/api'
import TypePill from '../components/TypePill'
import CopyButton from '../components/CopyButton'
import { IconArrowRight, IconSpinner, IconCode, IconKey, IconBolt } from '../components/icons'

export default function DatasetDetail() {
  const { id } = useParams()
  const [docs, setDocs] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setDocs(await apiGet(`/api/datasets/${id}/docs`))
    } catch (e) {
      setError(e.message)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  if (error) {
    return (
      <main className="container-page py-16">
        <p className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>
        <Link to="/dashboard" className="btn-ghost mt-4">← Back to dashboard</Link>
      </main>
    )
  }
  if (!docs) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-slate-400">
        <IconSpinner width={28} height={28} />
      </div>
    )
  }

  const fullUrl = `${API_URL}${docs.endpoint}`
  const exampleQuery = (docs.example.split('?')[1] || 'page=1&limit=25')

  return (
    <main className="container-page py-10">
      <Link to="/dashboard" className="text-sm text-slate-400 transition hover:text-white">← Dashboard</Link>
      <div className="mt-3 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-white">{docs.name}</h1>
        <span className="badge">API docs</span>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-5">
        {/* Left: reference */}
        <div className="space-y-6 lg:col-span-3">
          {/* Endpoint */}
          <section className="card p-6">
            <div className="flex items-center gap-2">
              <IconCode width={18} height={18} className="text-brand-300" />
              <h2 className="font-semibold text-white">Endpoint</h2>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-white/5 bg-black/30 px-4 py-3 font-mono text-sm">
              <span className="rounded bg-emerald-500/15 px-1.5 py-0.5 text-xs text-emerald-300">GET</span>
              <span className="break-all text-slate-300">{fullUrl}</span>
            </div>
            <p className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <IconKey width={14} height={14} /> Send your key as <code className="text-slate-300">Authorization: Bearer …</code>
            </p>
            <div className="mt-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-500">cURL</span>
                <CopyButton text={`curl "${fullUrl}?${exampleQuery}" \\\n  -H "Authorization: Bearer YOUR_API_KEY"`} />
              </div>
              <pre className="overflow-x-auto rounded-xl border border-white/5 bg-black/40 p-4 font-mono text-xs leading-relaxed text-slate-300">
{`curl "${fullUrl}?${exampleQuery}" \\
  -H "Authorization: Bearer YOUR_API_KEY"`}
              </pre>
            </div>
          </section>

          {/* Fields */}
          <section className="card p-6">
            <h2 className="font-semibold text-white">Fields</h2>
            <p className="mt-1 text-sm text-slate-400">Use these in filters and <code className="text-slate-300">sort</code>.</p>
            <div className="mt-4 overflow-hidden rounded-xl border border-white/5">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/[0.03] text-xs uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Field</th>
                    <th className="px-4 py-2.5 font-medium">Type</th>
                    <th className="px-4 py-2.5 font-medium">Operators</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {docs.fields.map((f) => (
                    <tr key={f.name} className="text-slate-300">
                      <td className="px-4 py-3 font-mono text-slate-200">{f.name}</td>
                      <td className="px-4 py-3"><TypePill type={f.data_type} /></td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1.5">
                          {f.operators.map((op) => (
                            <code key={op} className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[11px] text-slate-400">{op}</code>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 space-y-1.5 text-xs text-slate-500">
              <p><code className="text-slate-300">price__gt=20</code> — number/date comparisons (<code>gt, lt, gte, lte</code>)</p>
              <p><code className="text-slate-300">name__contains=oil</code> — text search</p>
              <p><code className="text-slate-300">sort=-rating</code> — descending sort · <code className="text-slate-300">page</code> &amp; <code className="text-slate-300">limit</code> — pagination</p>
            </div>
          </section>
        </div>

        {/* Right: live try-it */}
        <div className="lg:col-span-2">
          <TryIt baseUrl={fullUrl} defaultQuery={exampleQuery} />
        </div>
      </div>
    </main>
  )
}

function TryIt({ baseUrl, defaultQuery }) {
  const [apiKey, setApiKey] = useState('')
  const [query, setQuery] = useState(defaultQuery)
  const [resp, setResp] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    setResp(null)
    setStatus(null)
    try {
      const res = await fetch(`${baseUrl}?${query}`, {
        headers: apiKey ? { Authorization: `Bearer ${apiKey}` } : {},
      })
      setStatus(res.status)
      setResp(await res.json())
    } catch (e) {
      setResp({ error: e.message })
    } finally {
      setLoading(false)
    }
  }

  const statusColor = status == null ? '' : status < 300 ? 'text-emerald-300' : 'text-red-300'

  return (
    <section className="card sticky top-24 p-6">
      <div className="flex items-center gap-2">
        <IconBolt width={18} height={18} className="text-brand-300" />
        <h2 className="font-semibold text-white">Try it live</h2>
      </div>
      <div className="mt-4 space-y-3">
        <div>
          <label className="label">API key</label>
          <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            className="input font-mono text-xs" placeholder="sk_live_…" />
          <p className="mt-1 text-[11px] text-slate-500">Paste a key from your dashboard.</p>
        </div>
        <div>
          <label className="label">Query</label>
          <input value={query} onChange={(e) => setQuery(e.target.value)}
            className="input font-mono text-xs" placeholder="price__gt=20&sort=-rating" />
        </div>
        <button onClick={run} disabled={loading} className="btn-primary w-full">
          {loading ? <IconSpinner width={16} height={16} /> : <>Send request <IconArrowRight width={15} height={15} /></>}
        </button>
      </div>

      {status != null && (
        <div className="mt-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="font-medium uppercase tracking-wider text-slate-500">Response</span>
            <span className={`font-mono font-semibold ${statusColor}`}>{status}</span>
          </div>
          <pre className="max-h-80 overflow-auto rounded-xl border border-white/5 bg-black/40 p-4 font-mono text-xs leading-relaxed text-slate-300">
{JSON.stringify(resp, null, 2)}
          </pre>
        </div>
      )}
    </section>
  )
}
