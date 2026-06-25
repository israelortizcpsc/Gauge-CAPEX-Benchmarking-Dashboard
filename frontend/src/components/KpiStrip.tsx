import type { Portfolio, PortfolioKpis } from '../lib/api'
import { signedPct, pct, usdMillions } from '../lib/format'

function Kpi({
  label,
  value,
  sub,
  tone,
}: {
  label: string
  value: string
  sub?: string
  tone?: 'good' | 'bad'
}) {
  const toneClass = tone === 'good' ? ' is-good' : tone === 'bad' ? ' is-bad' : ''
  return (
    <div className="kpi">
      <div className="kpi__label">{label}</div>
      <div className={`kpi__value tnum${toneClass}`}>{value}</div>
      {sub && <div className="kpi__sub">{sub}</div>}
    </div>
  )
}

export function KpiStrip({ portfolio }: { portfolio: Portfolio }) {
  if (!portfolio.count) {
    return (
      <div className="state">No projects match the current filters.</div>
    )
  }
  const k = portfolio.kpis as PortfolioKpis

  return (
    <section className="kpis" aria-label="Portfolio summary">
      <Kpi label="Projects" value={portfolio.count.toLocaleString()} sub={`peer set of ${portfolio.peer_n.toLocaleString()}`} />
      <Kpi label="Total CAPEX" value={usdMillions(portfolio.total_capex)} sub="actual, completed" />
      <Kpi
        label="Cost Growth"
        value={signedPct(k.weighted_cost_growth)}
        sub="capex-weighted"
        tone={k.weighted_cost_growth > 0.05 ? 'bad' : k.weighted_cost_growth <= 0 ? 'good' : undefined}
      />
      <Kpi
        label="Schedule Slip"
        value={signedPct(k.median_schedule_slip)}
        sub="median"
        tone={k.median_schedule_slip > 0.05 ? 'bad' : k.median_schedule_slip <= 0 ? 'good' : undefined}
      />
      <Kpi
        label="Avg FEL Score"
        value={k.avg_fel_score.toFixed(0)}
        sub="0–100 readiness"
        tone={k.avg_fel_score >= 60 ? 'good' : k.avg_fel_score < 40 ? 'bad' : undefined}
      />
      <Kpi label="Over Budget" value={pct(k.pct_over_budget / 100, 0)} sub="of projects" />
    </section>
  )
}
