import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DependencyGraph, { EDGE_COLOR } from '../components/DependencyGraph'
import { api } from '../services/api'
import type { Analysis, DependencyResult, GraphData } from '../types/analysis'

const KINDS = ['extends', 'implements', 'calls', 'instantiates']

function isTestNode(id: string, path: string | null): boolean {
  const p = (path ?? '').toLowerCase()
  return p.includes('/test/') || p.startsWith('test/') || /tests?\b/i.test(id.split('.').slice(-2)[0] ?? '') || /Tests?(\.|$)/.test(id)
}

export default function AnalysisGraph() {
  const { id } = useParams()
  const jobId = Number(id)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [level, setLevel] = useState<'symbol' | 'type'>('type')
  const [raw, setRaw] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [deps, setDeps] = useState<DependencyResult | null>(null)
  const [dependents, setDependents] = useState<DependencyResult | null>(null)
  const [transitive, setTransitive] = useState(false)
  const [hideTests, setHideTests] = useState(true)
  const [hideUncertain, setHideUncertain] = useState(false)
  const [kinds, setKinds] = useState<Set<string>>(new Set(KINDS))

  useEffect(() => {
    api.getAnalysis(jobId).then(setAnalysis).catch((e) => setError((e as Error).message))
  }, [jobId])

  useEffect(() => {
    setLoading(true)
    setSelectedId(null)
    api
      .getGraph(jobId, level)
      .then((d) => {
        setRaw(d)
        setError(null)
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false))
  }, [jobId, level])

  // Apply filters on the client; the backend data is unchanged.
  const data: GraphData | null = useMemo(() => {
    if (!raw) return null
    const keep = new Set(
      raw.nodes.filter((n) => !(hideTests && isTestNode(n.id, n.path))).map((n) => n.id),
    )
    const edges = raw.edges
      .map((e) => ({ ...e, kinds: e.kinds.filter((k) => kinds.has(k)) }))
      .filter(
        (e) =>
          e.kinds.length > 0 &&
          keep.has(e.source) &&
          keep.has(e.target) &&
          !(hideUncertain && e.status !== 'resolved'),
      )
    return { ...raw, nodes: raw.nodes.filter((n) => keep.has(n.id)), edges }
  }, [raw, hideTests, hideUncertain, kinds])

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

  function toggleKind(k: string) {
    setKinds((prev) => {
      const next = new Set(prev)
      if (next.has(k)) next.delete(k)
      else next.add(k)
      return next
    })
  }

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
        <div className="ml-auto flex flex-wrap items-center gap-2">
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

      <div className="flex flex-wrap items-center gap-4 border-b border-slate-800 px-3 py-2 text-xs text-slate-300">
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={hideTests} onChange={(e) => setHideTests(e.target.checked)} />
          Hide test classes
        </label>
        <label className="flex items-center gap-1">
          <input
            type="checkbox"
            checked={hideUncertain}
            onChange={(e) => setHideUncertain(e.target.checked)}
          />
          Hide uncertain (dashed) links
        </label>
        <span className="text-slate-500">|</span>
        {KINDS.map((k) => (
          <label key={k} className="flex items-center gap-1">
            <input type="checkbox" checked={kinds.has(k)} onChange={() => toggleKind(k)} />
            <span className="inline-block h-0.5 w-4" style={{ background: EDGE_COLOR[k] }} />
            {k}
          </label>
        ))}
        {data && (
          <span className="ml-auto text-slate-500">
            {data.nodes.length} nodes · {data.edges.length} links
          </span>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <main className="relative min-h-[50vh] flex-1">
          {loading && <p className="p-4 text-slate-400">Loading graph...</p>}
          {error && (
            <div role="alert" className="m-4 rounded border border-red-800 bg-red-950 p-3 text-sm text-red-200">
              {error}
            </div>
          )}
          {!loading && data && data.nodes.length === 0 && (
            <p className="p-4 text-slate-400">Nothing to show with the current filters.</p>
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
            <div className="grid gap-2 text-sm text-slate-400">
              <p>
                Click a node to focus on it. An arrow A → B means A depends on B.
              </p>
              <p>
                <span className="text-orange-400">Orange</span> = depends on the selected node
                (could break if it changes).
                <br />
                <span className="text-cyan-300">Cyan</span> = what the selected node depends on.
              </p>
              <p>Dashed lines are uncertain (for example overloaded methods).</p>
            </div>
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
              <RelatedList
                title="Depends on"
                color="text-cyan-300"
                items={deps?.items}
                onPick={setSelectedId}
              />
              <RelatedList
                title="Used by (a change here can affect these)"
                color="text-orange-400"
                items={dependents?.items}
                onPick={setSelectedId}
                nodeIds={raw?.nodes.map((n) => n.id)}
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
  color: string
  items?: string[]
  onPick: (id: string) => void
  nodeIds?: string[]
}) {
  const known = props.nodeIds ? new Set(props.nodeIds) : null
  return (
    <div>
      <h2 className={`mb-1 font-medium ${props.color}`}>
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
                className="break-all text-left text-slate-200 hover:underline"
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
