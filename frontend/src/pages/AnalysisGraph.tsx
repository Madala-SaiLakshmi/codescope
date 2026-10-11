import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DependencyGraph from '../components/DependencyGraph'
import { api } from '../services/api'
import type { Analysis, DependencyResult, GraphData } from '../types/analysis'

export default function AnalysisGraph() {
  const { id } = useParams()
  const jobId = Number(id)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [level, setLevel] = useState<'symbol' | 'type'>('type')
  const [data, setData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [deps, setDeps] = useState<DependencyResult | null>(null)
  const [dependents, setDependents] = useState<DependencyResult | null>(null)
  const [transitive, setTransitive] = useState(false)

  useEffect(() => {
    api.getAnalysis(jobId).then(setAnalysis).catch((e) => setError((e as Error).message))
  }, [jobId])

  useEffect(() => {
    setLoading(true)
    setSelectedId(null)
    api
      .getGraph(jobId, level)
      .then((d) => {
        setData(d)
        setError(null)
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [jobId, level])

  useEffect(() => {
    if (!selectedId) {
      setDeps(null)
      setDependents(null)
      return
    }
    let cancelled = false
    Promise.all([
      api.getRelated(jobId, 'dependencies', selectedId, transitive),
      api.getRelated(jobId, 'dependents', selectedId, transitive),
    ])
      .then(([a, b]) => {
        if (!cancelled) {
          setDeps(a)
          setDependents(b)
        }
      })
      .catch((e) => !cancelled && setError((e as Error).message))
    return () => {
      cancelled = true
    }
  }, [jobId, selectedId, transitive])

  const matchIds = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q || !data) return null
    return new Set(data.nodes.filter((n) => n.id.toLowerCase().includes(q)).map((n) => n.id))
  }, [query, data])

  const selected = data?.nodes.find((n) => n.id === selectedId) ?? null

  return (
    <div className="flex h-screen flex-col bg-slate-950 text-slate-100">
      <header className="flex flex-wrap items-center gap-3 border-b border-slate-800 p-3">
        <Link
          to={analysis ? `/repositories/${analysis.repository_id}` : '/'}
          className="text-sm text-indigo-300 hover:underline"
        >
          ← Back
        </Link>
        <h1 className="font-semibold">Analysis #{jobId}</h1>
        {analysis?.revision && (
          <span className="text-xs text-slate-400">{analysis.revision.slice(0, 7)}</span>
        )}
        <div className="ml-auto flex items-center gap-2">
          <input
            aria-label="Search symbols"
            placeholder="Search..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded bg-slate-800 px-3 py-1 text-sm"
          />
          {matchIds && <span className="text-xs text-slate-400">{matchIds.size} matches</span>}
          <select
            aria-label="Graph level"
            value={level}
            onChange={(e) => setLevel(e.target.value as 'symbol' | 'type')}
            className="rounded bg-slate-800 px-2 py-1 text-sm"
          >
            <option value="type">Classes</option>
            <option value="symbol">Classes + methods</option>
          </select>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <main className="relative min-h-[50vh] flex-1">
          {loading && <p className="p-4 text-slate-400">Loading graph...</p>}
          {error && (
            <div role="alert" className="m-4 rounded border border-red-800 bg-red-950 p-3 text-sm text-red-200">
              {error}
            </div>
          )}
          {!loading && data && data.nodes.length === 0 && (
            <p className="p-4 text-slate-400">This analysis found no symbols.</p>
          )}
          {!loading && data && data.nodes.length > 0 && (
            <DependencyGraph
              data={data}
              selectedId={selectedId}
              matchIds={matchIds}
              onSelect={setSelectedId}
            />
          )}
        </main>

        <aside className="w-full overflow-y-auto border-t border-slate-800 p-4 md:w-96 md:border-l md:border-t-0">
          {!selected ? (
            <p className="text-sm text-slate-400">
              Click a node to see its details. Arrows point from a symbol to what it depends on.
            </p>
          ) : (
            <div className="grid gap-3 text-sm">
              <div>
                <div className="break-all font-medium">{selected.id}</div>
                <div className="text-slate-400">
                  {selected.kind}
                  {selected.path ? ` · ${selected.path}` : ''}
                  {selected.start_line ? `:${selected.start_line}-${selected.end_line}` : ''}
                </div>
              </div>
              <label className="flex items-center gap-2 text-slate-300">
                <input
                  type="checkbox"
                  checked={transitive}
                  onChange={(e) => setTransitive(e.target.checked)}
                />
                Include indirect (transitive)
              </label>
              <RelatedList title="Depends on" items={deps?.items} onPick={setSelectedId} />
              <RelatedList
                title="Used by (what a change here can affect)"
                items={dependents?.items}
                onPick={setSelectedId}
                level={level}
                nodeIds={data?.nodes.map((n) => n.id)}
              />
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}

function RelatedList(props: {
  title: string
  items?: string[]
  onPick: (id: string) => void
  level?: 'symbol' | 'type'
  nodeIds?: string[]
}) {
  const known = props.nodeIds ? new Set(props.nodeIds) : null
  return (
    <div>
      <h2 className="mb-1 font-medium">
        {props.title} {props.items ? `(${props.items.length})` : ''}
      </h2>
      {!props.items ? (
        <p className="text-slate-500">Loading...</p>
      ) : props.items.length === 0 ? (
        <p className="text-slate-500">None</p>
      ) : (
        <ul className="max-h-64 overflow-y-auto">
          {props.items.map((it) => (
            <li key={it}>
              <button
                onClick={() => props.onPick(it)}
                className="break-all text-left text-indigo-300 hover:underline"
              >
                {it}
              </button>
            </li>
          ))}
        </ul>
      )}
      {known && props.items && props.items.some((i) => !known.has(i)) && (
        <p className="mt-1 text-xs text-slate-500">
          Some items are methods and only appear on the "Classes + methods" graph.
        </p>
      )}
    </div>
  )
}
