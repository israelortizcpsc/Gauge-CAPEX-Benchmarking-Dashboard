import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { api, type Filters, type Meta } from './lib/api'
import { useAsync } from './hooks/useAsync'
import { Brand } from './components/Brand'
import { FilterBar } from './components/FilterBar'
import { KpiStrip } from './components/KpiStrip'
import { CostGapChart } from './components/CostGapChart'
import { FelGauge } from './components/FelGauge'
import { usdMillions } from './lib/format'

function Loading({ label }: { label: string }) {
  return <div className="state">{label}</div>
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="state state--error">
      Couldn’t load data: {message}. Is the API running on :8000?
    </div>
  )
}

export default function App() {
  const metaState = useAsync<Meta>(() => api.meta(), [])

  if (metaState.loading) return <Loading label="Loading…" />
  if (metaState.error || !metaState.data) return <ErrorState message={metaState.error ?? 'no data'} />

  return <Dashboard meta={metaState.data} />
}

function Dashboard({ meta }: { meta: Meta }) {
  const [filters, setFilters] = useState<Filters>({})
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const filterKey = JSON.stringify(filters)

  const portfolio = useAsync(() => api.portfolio(filters), [filterKey])
  const projects = useAsync(
    () => api.projects({ ...filters, ordering: 'name' }),
    [filterKey],
  )

  // When the filtered project list changes, keep the selection valid:
  // default to the first matching project.
  useEffect(() => {
    const rows = projects.data?.results ?? []
    if (rows.length === 0) {
      setSelectedId(null)
    } else if (!rows.some((p) => p.id === selectedId)) {
      setSelectedId(rows[0].id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projects.data])

  const benchmark = useAsync(
    () => (selectedId ? api.projectBenchmark(selectedId) : Promise.resolve(null)),
    [selectedId],
  )

  const selectedRow = useMemo(
    () => projects.data?.results.find((p) => p.id === selectedId) ?? null,
    [projects.data, selectedId],
  )

  return (
    <div className="app">
      <header className="masthead">
        <Brand />
        <p className="masthead__note">
          Demonstration on <strong>synthetic data</strong> — ~2,000 generated sustaining-capital
          projects. No real client data.
        </p>
      </header>

      <FilterBar meta={meta} filters={filters} onChange={setFilters} />

      {portfolio.loading && !portfolio.data ? (
        <Loading label="Loading portfolio…" />
      ) : portfolio.error ? (
        <ErrorState message={portfolio.error} />
      ) : portfolio.data ? (
        <KpiStrip portfolio={portfolio.data} />
      ) : null}

      <div className="grid">
        <section className="card" aria-label="Project cost-gap benchmark">
          <div className="card__head">
            <h2 className="card__title">Cost-gap vs peer norms</h2>
            <button type="button" className="filters__reset" onClick={() => window.print()}>
              Export report
            </button>
          </div>

          <div className="picker">
            <label className="visually-hidden" htmlFor="project-picker">
              Select a project to benchmark
            </label>
            <select
              id="project-picker"
              value={selectedId ?? ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
              disabled={!projects.data?.results.length}
            >
              {(projects.data?.results ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.sector_label}
                </option>
              ))}
            </select>
            {projects.data && (
              <span className="picker__meta">
                {projects.data.count.toLocaleString()} projects in view
              </span>
            )}
          </div>

          {selectedRow && (
            <p className="card__sub" style={{ marginTop: 14, marginBottom: 0 }}>
              {selectedRow.operator} · {selectedRow.project_type_label} · {selectedRow.region_label} ·
              sanctioned {selectedRow.sanction_year} · {usdMillions(selectedRow.capex_actual)} actual
            </p>
          )}

          <div style={{ marginTop: 8 }}>
            {benchmark.loading && !benchmark.data ? (
              <Loading label="Computing benchmark…" />
            ) : benchmark.error ? (
              <ErrorState message={benchmark.error} />
            ) : benchmark.data ? (
              <CostGapChart benchmark={benchmark.data} metrics={meta.metrics} />
            ) : (
              <Loading label="Select a project to benchmark." />
            )}
          </div>
        </section>

        <section className="card" aria-label="FEL readiness">
          <div className="card__head">
            <h2 className="card__title">FEL readiness</h2>
            <span className="card__hint">front-end loading</span>
          </div>
          <p className="card__sub">
            How well the project was defined at sanction — the strongest predictor of cost and
            schedule outcome.
          </p>
          {benchmark.data ? (
            <FelGauge fel={benchmark.data.fel} />
          ) : (
            <Loading label="—" />
          )}
        </section>
      </div>

      <footer className="footer">
        <span>
          Gauge · sustaining-CAPEX benchmarking · React + TypeScript · Django REST Framework
        </span>
        <span className="footer__print">
          Benchmark math is computed server-side for a single source of truth.
        </span>
      </footer>
    </div>
  )
}
