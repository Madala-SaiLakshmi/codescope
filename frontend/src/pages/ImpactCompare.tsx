import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { impactApi } from '../services/impactApi'
import type { ImpactReport } from '../types/impact'

export default function ImpactCompare() {
  const { id } = useParams()
  const repoId = Number(id)
  const navigate = useNavigate()
  const [base, setBase] = useState('HEAD~5')
  const [target, setTarget] = useState('HEAD')
  const [reports, setReports] = useState<ImpactReport[]>([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    impactApi.list(repoId).then(setReports).catch((e) => setError((e as Error).message))
  }, [repoId])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setRunning(true)
    setError(null)
    try {
      const report = await impactApi.create(repoId, base.trim(), target.trim())
      navigate(`/impact/${report.id}`)
    } catch (err) {
      setError((err as Error).message)
      setRunning(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="mx-auto max-w-3xl">
        <Link to={`/repositories/${repoId}`} className="text-sm text-indigo-300 hover:underline">
          ← Repository
        </Link>
        <h1 className="mt-4 text-2xl font-semibold">Compare revisions</h1>
        <p className="mb-4 text-sm text-slate-400">
          Use commit SHAs or names like HEAD~10 within the last 200 commits of the default branch.
        </p>

        <form onSubmit={onSubmit} className="mb-6 grid gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4">
          <label className="grid gap-1 text-sm">
            Base (older)
            <input className="rounded bg-slate-800 px-3 py-2" value={base}
                   onChange={(e) => setBase(e.target.value)} required />
          </label>
          <label className="grid gap-1 text-sm">
            Target (newer)
            <input className="rounded bg-slate-800 px-3 py-2" value={target}
                   onChange={(e) => setTarget(e.target.value)} required />
          </label>
          <button type="submit" disabled={running}
                  className="rounded bg-indigo-600 px-4 py-2 font-medium disabled:opacity-50">
            {running ? 'Cloning and analyzing both revisions... (can take a minute)' : 'Analyze change impact'}
          </button>
        </form>

        {error && (
          <div role="alert" className="mb-4 rounded border border-red-800 bg-red-950 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        <h2 className="mb-3 text-lg font-medium">Previous reports</h2>
        {reports.length === 0 ? (
          <p className="text-slate-400">No reports yet.</p>
        ) : (
          <ul className="grid gap-3">
            {reports.map((r) => (
              <li key={r.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                <Link to={`/impact/${r.id}`} className="font-medium text-indigo-300 hover:underline">
                  #{r.id} · {r.base_revision} → {r.target_revision}
                </Link>
                <div className="text-sm text-slate-400">
                  {r.status === 'succeeded'
                    ? `${r.changed_file_count} files · ${r.changed_symbol_count} changed · ${r.affected_count} affected`
                    : r.error_summary ?? r.status}
                </div>
                <div className="text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
