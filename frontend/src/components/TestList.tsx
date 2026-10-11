import type { SelectedTest } from '../types/impact'

const BADGE: Record<string, string> = {
  high: 'bg-emerald-900 text-emerald-200',
  medium: 'bg-amber-900 text-amber-200',
  low: 'bg-slate-800 text-slate-300',
}

export default function TestList({ tests }: { tests: SelectedTest[] }) {
  if (tests.length === 0) {
    return <p className="text-sm text-slate-500">No tests were selected for this change.</p>
  }
  return (
    <ul className="grid gap-2">
      {tests.map((t) => (
        <li key={t.test_path} className="rounded border border-slate-800 bg-slate-900 p-3 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium">{t.test_path.split('/').pop()}</span>
            <span className={`rounded px-2 py-0.5 text-xs ${BADGE[t.confidence] ?? ''}`}>
              {t.confidence}
            </span>
            <span className="ml-auto text-xs text-slate-400">score {t.score}</span>
          </div>
          <div className="break-all text-xs text-slate-500">{t.test_path}</div>
          <ul className="mt-1 list-disc pl-5 text-xs text-slate-400">
            {t.reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}