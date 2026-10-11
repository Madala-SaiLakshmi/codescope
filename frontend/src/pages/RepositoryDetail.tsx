import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../services/api'
import type { Analysis } from '../types/analysis'
import type { Repository } from '../types/repository'

const STATUS_STYLE: Record<string, string> = {
  succeeded: 'text-emerald-300',
  failed: 'text-red-300',
  running: 'text-amber-300',
  queued: 'text-slate-300',
}

export default function RepositoryDetail() {
  const { id } = useParams()
  const repoId = Number(id)
  const [repo, setRepo] = useState<Repository | null>(null)
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [r, a] = await Promise.all([api.getRepository(repoId), api.listAnalyses(repoId)])
      setRepo(r)
      setAnalyses(a)
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [repoId])

  useEffect(() => {
    load()
  }, [load])

  async function analyze() {
    setRunning(true)
    setError(null)
    try {
      await api.startAnalysis(repoId)
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="mx-auto max-w-3xl">
        <Link to="/" className="text-sm text-indigo-300 hover:underline">
          ← All repositories
        </Link>
        {loading ? (
          <p className="mt-6 text-slate-400">Loading...</p>
        ) : (
          <>
            <h1 className="mt-4 text-2xl font-semibold">{repo?.name ?? 'Repository'}</h1>
            <p className="mb-6 text-sm text-slate-400">{repo?.source_url}</p>

            <button
              onClick={analyze}
              disabled={running || !repo}
              className="mb-6 rounded bg-indigo-600 px-4 py-2 font-medium disabled:opacity-50"
            >
              {running ? 'Analyzing... (this can take a minute)' : 'Analyze repository'}
            </button>

            {error && (
              <div role="alert" className="mb-4 rounded border border-red-800 bg-red-950 p-3 text-sm text-red-200">
                {error}
              </div>
            )}

            <h2 className="mb-3 text-lg font-medium">Analysis history</h2>
            {analyses.length === 0 ? (
              <p className="text-slate-400">No analyses yet. Click "Analyze repository".</p>
            ) : (
              <ul className="grid gap-3">
                {analyses.map((a) => (
                  <li key={a.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                    <div className="flex items-center justify-between">
                      <span className={`font-medium ${STATUS_STYLE[a.status] ?? ''}`}>
                        #{a.id} · {a.status}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(a.created_at).toLocaleString()}
                      </span>
                    </div>
                    {a.status === 'succeeded' && (
                      <div className="mt-1 text-sm text-slate-400">
                        {a.file_count} files · {a.symbol_count} symbols · {a.edge_count} edges
                        {a.revision ? ` · ${a.revision.slice(0, 7)}` : ''}
                      </div>
                    )}
                    {a.error_summary && (
                      <div className="mt-1 text-sm text-red-300">{a.error_summary}</div>
                    )}
                    {a.status === 'succeeded' && (
                      <Link
                        to={`/analyses/${a.id}`}
                        className="mt-2 inline-block text-sm text-indigo-300 hover:underline"
                      >
                        View dependency graph →
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </div>
  )
}
