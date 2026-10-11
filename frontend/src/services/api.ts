import type { Repository, RepositoryCreate } from '../types/repository'
import type { Analysis, DependencyResult, GraphData } from '../types/analysis'

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join('; ')
          : `Request failed (${res.status})`
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  listRepositories: () => request<Repository[]>('/api/repositories'),
  getRepository: async (id: number) => {
    const all = await request<Repository[]>('/api/repositories')
    const repo = all.find((r) => r.id === id)
    if (!repo) throw new Error('Repository not found')
    return repo
  },
  createRepository: (data: RepositoryCreate) =>
    request<Repository>('/api/repositories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  startAnalysis: (repositoryId: number) =>
    request<Analysis>(`/api/repositories/${repositoryId}/analyses`, { method: 'POST' }),
  listAnalyses: (repositoryId: number) =>
    request<Analysis[]>(`/api/repositories/${repositoryId}/analyses`),
  getAnalysis: (id: number) => request<Analysis>(`/api/analyses/${id}`),
  getGraph: (id: number, level: 'symbol' | 'type') =>
    request<GraphData>(`/api/analyses/${id}/graph?level=${level}`),
  getRelated: (
    id: number,
    relation: 'dependencies' | 'dependents',
    symbol: string,
    transitive: boolean,
  ) =>
    request<DependencyResult>(
      `/api/analyses/${id}/${relation}?symbol=${encodeURIComponent(symbol)}&transitive=${transitive}`,
    ),
}
