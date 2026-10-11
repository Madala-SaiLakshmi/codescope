import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { RiskFactor } from '../types/impact'

const LEVEL_COLOR: Record<string, string> = {
  low: '#34d399',
  medium: '#fbbf24',
  high: '#fb923c',
  critical: '#f87171',
}

interface Props {
  score: number | null
  level: string | null
  factors: RiskFactor[]
}

export default function RiskCard({ score, level, factors }: Props) {
  if (score === null || !level) {
    return <p className="text-sm text-slate-500">No risk score for this report (created before scoring existed).</p>
  }
  const color = LEVEL_COLOR[level] ?? '#94a3b8'
  const data = factors.map((f) => ({ name: f.name, points: f.points, max: f.max_points, detail: f.detail }))

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="mb-3 flex items-baseline gap-3">
        <span className="text-4xl font-semibold" style={{ color }}>{score}</span>
        <span className="text-sm uppercase tracking-wide" style={{ color }}>{level} risk</span>
        <span className="text-xs text-slate-500">out of 100</span>
      </div>

      <div style={{ width: '100%', height: 240 }}>
        <ResponsiveContainer>
          <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid stroke="#1e293b" horizontal={false} />
            <XAxis type="number" domain={[0, 30]} stroke="#64748b" />
            <YAxis type="category" dataKey="name" width={130} stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #334155' }}
              formatter={(value, _n, item) => [`${value} / ${item.payload.max}`, 'Points']}
              labelFormatter={() => ''}
            />
            <Bar dataKey="points" radius={[0, 4, 4, 0]}>
              {data.map((d) => (
                <Cell key={d.name} fill={color} fillOpacity={0.4 + 0.6 * (d.points / d.max || 0)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <ul className="mt-3 grid gap-1 text-xs text-slate-400">
        {factors.map((f) => (
          <li key={f.name}>
            <span className="text-slate-200">{f.name}</span> ({f.points}/{f.max_points}): {f.detail}
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-500">
        A rule-based score with documented weights, not a trained model. It is a guide for where to look first.
      </p>
    </div>
  )
}