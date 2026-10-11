export interface ImpactReport {
  id: number
  repository_id: number
  base_revision: string
  target_revision: string
  base_sha: string | null
  target_sha: string | null
  base_job_id: number | null
  target_job_id: number | null
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  error_summary: string | null
  created_at: string
  completed_at: string | null
  changed_file_count: number
  changed_symbol_count: number
  affected_count: number
  uncertainty_count: number
}

export interface FileChange {
  path: string
  old_path: string | null
  change_type: string
}

export interface ChangedSymbol {
  qualified_name: string
  kind: string
  path: string | null
  change: string | null
}

export interface AffectedSymbol {
  qualified_name: string
  kind: string
  path: string | null
  distance: number
  certain: boolean
  root: string
  via: string[]
}

export interface Uncertainty {
  path: string
  message: string
}

export interface ImpactReportDetail extends ImpactReport {
  files: FileChange[]
  changed: ChangedSymbol[]
  affected: AffectedSymbol[]
  uncertainties: Uncertainty[]
  risk_score: number | null
  risk_level: 'low' | 'medium' | 'high' | 'critical' | null
  risk_factors: RiskFactor[]
  import_changes: Uncertainty[]
  tests: SelectedTest[]
}

export interface RiskFactor {
  name: string
  points: number
  max_points: number
  detail: string
}

export interface SelectedTest {
  test_path: string
  test_class: string
  score: number
  confidence: 'high' | 'medium' | 'low'
  reasons: string[]
}