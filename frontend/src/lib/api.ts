// Typed client for the Gauge benchmark API.
//
// All requests go through `request()`, which resolves the base URL from
// VITE_API_BASE (empty in dev so Vite's proxy handles same-origin /api calls).

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

// In static mode (the GitHub Pages demo) there's no live backend — the app
// reads a frozen JSON snapshot of the real Django API committed under
// public/demo-api. `STATIC` flips every endpoint to file reads.
export const STATIC = import.meta.env.VITE_STATIC === '1'
const STATIC_BASE = `${import.meta.env.BASE_URL}demo-api`

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(`${API_BASE}/api${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value)
    }
  }
  const res = await fetch(url.toString(), { headers: { Accept: 'application/json' } })
  if (!res.ok) {
    throw new ApiError(res.status, `Request to ${path} failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

// Canonical snapshot filename for a peer group — must match the backend's
// export_static.sig_filename(): dims in fixed order, `dim-value`, joined by `__`.
function sigFile(filters: Filters): string {
  const order: (keyof Filters)[] = ['sector', 'region', 'project_type', 'size_band']
  const parts = order.filter((d) => filters[d]).map((d) => `${d}-${filters[d]}`)
  return parts.length === 0 ? 'all' : parts.join('__')
}

async function staticGet<T>(file: string): Promise<T> {
  const res = await fetch(`${STATIC_BASE}/${file}`, { headers: { Accept: 'application/json' } })
  if (!res.ok) {
    throw new ApiError(res.status, `Snapshot ${file} not available in the static demo`)
  }
  return res.json() as Promise<T>
}

// --- Shared types -----------------------------------------------------------

export type MetricKey = 'capex_intensity' | 'cost_growth' | 'schedule_slip'

export interface Option {
  value: string
  label: string
}

export interface MetricMeta {
  key: MetricKey
  label: string
  unit: string
  higher_is_worse: boolean
}

export interface Meta {
  sectors: Option[]
  regions: Option[]
  project_types: Option[]
  size_bands: Option[]
  metrics: MetricMeta[]
  fel_bands: { min: number; label: string }[]
}

export interface ProjectRow {
  id: number
  name: string
  operator: string
  sector: string
  sector_label: string
  region: string
  region_label: string
  project_type: string
  project_type_label: string
  size_band: string
  sanction_year: number
  capex_estimate: number
  capex_actual: number
  cost_growth: number
  schedule_slip: number
  fel_score: number
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Distribution {
  n: number
  mean: number
  p10: number
  p25: number
  p50: number
  p75: number
  p80: number
  p90: number
}

export interface ProjectMetric {
  value: number
  percentile_rank: number
  gap_vs_p50: number | null
  gap_vs_p80: number | null
  distribution: Distribution | null
}

export interface Fel {
  score: number
  band: string
  components: Record<'scope' | 'engineering' | 'execution', number>
}

export interface ProjectBenchmark {
  project_id: number
  peer_group: { filters: Record<string, string>; n: number; is_exact: boolean }
  metrics: Record<MetricKey, ProjectMetric>
  fel: Fel
}

export interface PortfolioKpis {
  weighted_cost_growth: number
  median_cost_growth: number
  median_schedule_slip: number
  avg_fel_score: number
  pct_over_budget: number
  pct_capex_over_peer_norm: number
}

export interface Portfolio {
  filters: Record<string, string>
  count: number
  total_capex: number
  peer_n: number
  kpis: PortfolioKpis | Record<string, never>
}

export type Filters = {
  sector?: string
  region?: string
  project_type?: string
  size_band?: string
}

// --- Endpoints --------------------------------------------------------------

export const api = {
  meta: () =>
    STATIC ? staticGet<Meta>('meta.json') : request<Meta>('/meta/'),

  projects: (filters: Filters & { search?: string; ordering?: string; page?: string }) =>
    STATIC
      ? staticGet<Paginated<ProjectRow>>(`projects/${sigFile(filters)}.json`)
      : request<Paginated<ProjectRow>>('/projects/', filters),

  benchmark: (filters: Filters) =>
    STATIC
      ? staticGet<Distribution & { signature: string }>(`benchmarks/${sigFile(filters)}.json`)
      : request<Distribution & { signature: string }>('/benchmarks/', filters),

  portfolio: (filters: Filters) =>
    STATIC
      ? staticGet<Portfolio>(`portfolio/${sigFile(filters)}.json`)
      : request<Portfolio>('/portfolio/', filters),

  projectBenchmark: (id: number) =>
    STATIC
      ? staticGet<ProjectBenchmark>(`project-benchmark/${id}.json`)
      : request<ProjectBenchmark>(`/projects/${id}/benchmark/`),
}
