export interface Analysis {
  id: number
  repository_id: number
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  revision: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  error_summary: string | null
  file_count: number
  symbol_count: number
  edge_count: number
}

export interface GraphNode {
  id: string
  label: string
  kind: string
  path: string | null
  start_line: number | null
  end_line: number | null
  parent: string | null
}

export interface GraphEdge {
  source: string
  target: string
  kinds: string[]
  status: string
}

export interface GraphData {
  job_id: number
  level: 'symbol' | 'type'
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface DependencyResult {
  symbol: string
  relation: 'dependencies' | 'dependents'
  transitive: boolean
  include_uncertain: boolean
  items: string[]
}
