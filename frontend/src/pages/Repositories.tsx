import { Link } from 'react-router-dom'
import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../services/api'
import type { Repository } from '../types/repository'

export default function Repositories() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    try {
      setRepos(await api.listRepositories())
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await api.createRepository({ name, source_url: url })
      setName('')
      setUrl('')
      await load()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-semibold">CodeScope</h1>
        <p className="text-slate-400 mb-6">Repositories</p>

        <form
          onSubmit={onSubmit}
          className="mb-6 grid gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4"
        >
          <label className="grid gap-1 text-sm">
            Name
            <input
              className="rounded bg-slate-800 px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </label>
          <label className="grid gap-1 text-sm">
            Git URL (https only)
            <input
              className="rounded bg-slate-800 px-3 py-2"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              required
            />
          </label>
          <button
            type="submit"
            disabled={submitting}
            className="rounded bg-indigo-600 px-4 py-2 font-medium disabled:opacity-50"
          >
            {submitting ? 'Saving...' : 'Add repository'}
          </button>
        </form>

        {error && (
          <div role="alert" className="mb-4 rounded border border-red-800 bg-red-950 p-3 text-sm text-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <p className="text-slate-400">Loading...</p>
        ) : repos.length === 0 ? (
          <p className="text-slate-400">No repositories yet. Add one above.</p>
        ) : (
          <ul className="grid gap-3">
            {repos.map((r) => (
              <li key={r.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
                <Link to={`/repositories/${r.id}`} className="font-medium text-indigo-300 hover:underline">
                  {r.name}
                </Link>
                <div className="text-sm text-slate-400">{r.source_url}</div>
                <div className="text-xs text-slate-500">
                  {r.default_branch} · {new Date(r.created_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}