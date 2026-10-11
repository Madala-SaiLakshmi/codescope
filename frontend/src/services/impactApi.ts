import { request } from './api'
import type { ImpactReport, ImpactReportDetail } from '../types/impact'

export const impactApi = {
  create: (repositoryId: number, base: string, target: string) =>
    request<ImpactReport>(`/api/repositories/${repositoryId}/impact-reports`, {
      method: 'POST',
      body: JSON.stringify({ base, target }),
    }),
  list: (repositoryId: number) =>
    request<ImpactReport[]>(`/api/repositories/${repositoryId}/impact-reports`),
  get: (id: number) => request<ImpactReportDetail>(`/api/impact-reports/${id}`),
}
