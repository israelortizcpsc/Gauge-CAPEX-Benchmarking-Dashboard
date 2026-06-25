import type { MetricKey, MetricMeta, ProjectBenchmark, ProjectMetric } from '../lib/api'
import { num, pct, percentileLabel, signedPct } from '../lib/format'

interface Props {
  benchmark: ProjectBenchmark
  metrics: MetricMeta[]
}

// Where a value lands on a 0..100 track spanning the peer distribution.
function position(value: number, lo: number, hi: number): number {
  if (hi <= lo) return 50
  return Math.max(0, Math.min(100, ((value - lo) / (hi - lo)) * 100))
}

function rankTone(rank: number): string {
  // All benchmarked metrics are "higher is worse", so a low percentile rank is
  // good (cheaper / faster than peers).
  if (rank <= 40) return 'rank-good'
  if (rank <= 70) return 'rank-mid'
  return 'rank-bad'
}

function formatValue(metric: MetricKey, value: number): string {
  return metric === 'capex_intensity' ? num(value, 2) : signedPct(value)
}

function MetricRow({ metric, data }: { metric: MetricMeta; data: ProjectMetric }) {
  const dist = data.distribution
  if (!dist) {
    return (
      <div className="metric-row">
        <div className="metric-row__name">{metric.label}</div>
        <div className="card__hint">Not enough peers to benchmark.</div>
      </div>
    )
  }

  // Domain padded slightly beyond p10..p90 and the project value itself.
  const lo = Math.min(dist.p10, data.value)
  const hi = Math.max(dist.p90, data.value)
  const pad = (hi - lo) * 0.08 || 1
  const min = lo - pad
  const max = hi + pad

  const p10 = position(dist.p10, min, max)
  const p90 = position(dist.p90, min, max)
  const p25 = position(dist.p25, min, max)
  const p75 = position(dist.p75, min, max)
  const p50 = position(dist.p50, min, max)
  const p80 = position(dist.p80, min, max)
  const proj = position(data.value, min, max)

  const gap = data.gap_vs_p50
  const gapGood = gap !== null && gap <= 0
  const valueText = formatValue(metric.key, data.value)

  const ariaLabel =
    `${metric.label}: this project ${valueText}, ` +
    `${percentileLabel(data.percentile_rank)} of peers. ` +
    `Peer median (P50) ${formatValue(metric.key, dist.p50)}, ` +
    `top-quintile target (P80) ${formatValue(metric.key, dist.p80)}.`

  return (
    <div className="metric-row">
      <div className="metric-row__head">
        <span className="metric-row__name">{metric.label}</span>
        <span className={`metric-row__rank ${rankTone(data.percentile_rank)}`}>
          {percentileLabel(data.percentile_rank)}
        </span>
      </div>

      <div className="bar-track" role="img" aria-label={ariaLabel}>
        {/* p10–p90 spread */}
        <div className="bar-range" style={{ left: `${p10}%`, width: `${p90 - p10}%` }} />
        {/* p25–p75 interquartile, darker */}
        <div className="bar-iqr" style={{ left: `${p25}%`, width: `${p75 - p25}%` }} />
        {/* P50 / P80 reference markers */}
        <div className="bar-ref bar-ref--p50" style={{ left: `${p50}%` }} title="Peer median (P50)" />
        <div className="bar-ref bar-ref--p80" style={{ left: `${p80}%` }} title="Target (P80)" />
        {/* Project marker */}
        <div
          className={`bar-proj ${gapGood ? 'is-good' : 'is-bad'}`}
          style={{ left: `${proj}%` }}
        >
          <span className="bar-proj__value tnum">{valueText}</span>
        </div>
      </div>

      <div className="metric-foot">
        <span>
          vs peer P50:{' '}
          <span className={`gap-callout ${gapGood ? 'is-good' : 'is-bad'}`}>
            {gap === null ? '—' : signedPct(gap)}
          </span>
        </span>
        <span>
          vs P80 target:{' '}
          <span className="tnum">{data.gap_vs_p80 === null ? '—' : signedPct(data.gap_vs_p80)}</span>
        </span>
      </div>
    </div>
  )
}

export function CostGapChart({ benchmark, metrics }: Props) {
  const peer = benchmark.peer_group
  return (
    <div>
      <p className="card__sub">
        Benchmarked against{' '}
        <strong>{peer.n.toLocaleString()}</strong> comparable projects
        {peer.is_exact ? '' : ' (peer group widened for a robust sample)'}. Lower is better on
        every metric.
      </p>

      {metrics.map((m) => (
        <MetricRow key={m.key} metric={m} data={benchmark.metrics[m.key]} />
      ))}

      <div className="legend" aria-hidden="true">
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: 'var(--surface-sunken)', border: '1px solid var(--line-strong)' }} />
          P10–P90 spread
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ background: '#d7dde4' }} />
          P25–P75
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ width: 3, height: 14, borderRadius: 1, background: 'var(--navy)' }} />
          P50 median
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ width: 3, height: 14, borderRadius: 1, background: 'var(--accent)' }} />
          P80 target
        </span>
        <span className="legend__item">
          <span className="legend__swatch" style={{ borderRadius: '50%', width: 12, height: 12, background: 'var(--good)' }} />
          This project
        </span>
      </div>

      {/* Screen-reader / no-CSS fallback table of the same numbers. */}
      <table className="visually-hidden">
        <caption>Benchmark values for the selected project</caption>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Project</th>
            <th>Percentile</th>
            <th>P50</th>
            <th>P80</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => {
            const d = benchmark.metrics[m.key]
            return (
              <tr key={m.key}>
                <td>{m.label}</td>
                <td>{formatValue(m.key, d.value)}</td>
                <td>{pct(d.percentile_rank / 100, 0)}</td>
                <td>{d.distribution ? formatValue(m.key, d.distribution.p50) : '—'}</td>
                <td>{d.distribution ? formatValue(m.key, d.distribution.p80) : '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
