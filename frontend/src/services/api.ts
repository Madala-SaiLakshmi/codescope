import { clearToken, getToken, setToken } from './auth'
import type { Repository, RepositoryCreate } from '../types/repository'
import type { Analysis, DependencyResult, GraphData } from '../types/analysis'

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (res.status === 401 && !path.startsWith('/api/auth/login')) {
    clearToken()
    window.location.assign('/login')
    throw new Error('Session expired, please sign in again')
  }
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

export const authApi = {
  register: (email: string, password: string) =>
    request<{ id: number; email: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  login: async (email: string, password: string) => {
    const res = await request<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    setToken(res.access_token)
  },
  logout: () => clearToken(),
}