import RiskCard from '../components/RiskCard'
import TestList from '../components/TestList'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { impactApi } from '../services/impactApi'
import type { ImpactReportDetail } from '../types/impact'

const CHANGE_STYLE: Record<string, string> = {
  added: 'text-emerald-300',
  modified: 'text-amber-300',
  removed: 'text-red-300',
  deleted: 'text-red-300',
  renamed: 'text-sky-300',
}

function short(name: string): string {
  return name.split('.').slice(-3).join('.')
}

export default function ImpactReportView() {
  const { id } = useParams()
  const [report, setReport] = useState<ImpactReportDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    impactApi.get(Number(id)).then(setReport).catch((e) => setError((e as Error).message))
  }, [id])

  if (error) {
    return <p role="alert" className="p-8 text-red-300">{error}</p>
  }
  if (!report) return <p className="p-8 text-slate-400">Loading...</p>

  return (
    <div className="min-h-screen bg-slate-950 p-8 text-slate-100">
      <div className="mx-auto max-w-4xl">
        <Link to={`/repositories/${report.repository_id}/compare`} className="text-sm text-indigo-300 hover:underline">
          ← Reports
        </Link>
        <h1 className="mt-4 text-2xl font-semibold">Change impact #{report.id}</h1>
        <p className="mb-4 text-sm text-slate-400">
          {report.base_revision} ({report.base_sha?.slice(0, 7) ?? '?'}) →{' '}
          {report.target_revision} ({report.target_sha?.slice(0, 7) ?? '?'})
        </p>

        {report.status === 'failed' ? (
          <div role="alert" className="rounded border border-red-800 bg-red-950 p-3 text-red-200">
            {report.error_summary ?? 'Analysis failed'}
          </div>
        ) : (
          <>
            <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
              {[
                ['Files changed', report.changed_file_count],
                ['Symbols changed', report.changed_symbol_count],
                ['Potentially affected', report.affected_count],
                ['Could not map', report.uncertainty_count],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                  <div className="text-2xl font-semibold">{value}</div>
                  <div className="text-xs text-slate-400">{label}</div>
                </div>
              ))}
            </div>

            <Section title="Risk score">
              <RiskCard score={report.risk_score} level={report.risk_level} factors={report.risk_factors} />
            </Section>

            <Section title={`Suggested tests (${report.tests.length})`}>
              <TestList tests={report.tests} />
            </Section>

            <Section title={`Changed files (${report.files.length})`}>
              {report.files.map((f) => (
                <li key={f.path} className="break-all">
                  <span className={CHANGE_STYLE[f.change_type] ?? ''}>{f.change_type}</span>{' '}
                  {f.old_path && f.old_path !== f.path ? `${f.old_path} → ` : ''}
                  {f.path}
                </li>
              ))}
            </Section>

            <Section title={`Changed symbols (${report.changed.length})`}>
              {report.changed.map((c) => (
                <li key={c.qualified_name + c.change} className="break-all">
                  <span className={CHANGE_STYLE[c.change ?? ''] ?? ''}>{c.change}</span>{' '}
                  {c.qualified_name} <span className="text-slate-500">({c.kind})</span>
                </li>
              ))}
            </Section>

            <Section title={`Potentially affected (${report.affected.length})`}>
              {report.affected.length === 0 && <li className="text-slate-500">None found.</li>}
              {report.affected.map((a) => (
                <li key={a.qualified_name} className="mb-2 break-all">
                  <div>
                    {a.qualified_name}{' '}
                    <span className="text-xs text-slate-500">
                      distance {a.distance} · {a.certain ? 'confirmed path' : 'uncertain path'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400">
                    Why: {a.via.map(short).join(' → ')} (each depends on the next)
                  </div>
                </li>
              ))}
            </Section>

            <Section title={`Could not be traced (${report.uncertainties.length})`}>
              {report.uncertainties.length === 0 && <li className="text-slate-500">None.</li>}
              {report.uncertainties.map((u, i) => (
                <li key={i} className="break-all">
                  <span className="text-slate-300">{u.path}</span>
                  <div className="text-xs text-slate-400">{u.message}</div>
                </li>
              ))}
            </Section>

              {report.import_changes.length > 0 && (
              <Section title={`Import-only edits (${report.import_changes.length}, not traced)`}>
                {report.import_changes.map((u, i) => (
                  <li key={i} className="break-all text-xs text-slate-400">{u.path}: {u.message}</li>
                ))}
              </Section>
            )}

            <p className="mt-6 text-xs text-slate-500">
              Results are based on static analysis. Calls on variables whose type is unknown are
              not traced, so this is a guide, not a guarantee.
            </p>
          </>
        )}
      </div>
    </div>
  )
}

function Section(props: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6">
      <h2 className="mb-2 text-lg font-medium">{props.title}</h2>
      <ul className="max-h-96 overflow-y-auto rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm">
        {props.children}
      </ul>
    </section>
  )
}
