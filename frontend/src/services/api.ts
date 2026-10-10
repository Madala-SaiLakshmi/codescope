import type { Repository, RepositoryCreate } from '../types/repository'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
  createRepository: (data: RepositoryCreate) =>
    request<Repository>('/api/repositories', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
}