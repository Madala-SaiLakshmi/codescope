export interface Repository {
  id: number
  name: string
  source_type: string
  source_url: string | null
  default_branch: string
  created_at: string
}

export interface RepositoryCreate {
  name: string
  source_url: string
  default_branch?: string
}