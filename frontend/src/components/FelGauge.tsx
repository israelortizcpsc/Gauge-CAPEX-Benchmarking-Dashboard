import type { Fel } from '../lib/api'

// Radial gauge for the 0..100 FEL readiness score. Built from SVG arcs so it
// scales cleanly and carries an accessible label / role.

const COMPONENT_LABELS: Record<keyof Fel['components'], string> = {
  scope: 'Scope Definition',
  engineering: 'Engineering Maturity',
  execution: 'Execution Planning',
}

// Arc geometry: a 240° sweep from 150° to 30° (clockwise through the bottom).
const START = 150
const SWEEP = 240
const R = 70
const CX = 90
const CY = 90

function polar(angleDeg: number): [number, number] {
  const a = (angleDeg * Math.PI) / 180
  return [CX + R * Math.cos(a), CY + R * Math.sin(a)]
}

function arcPath(fromScore: number, toScore: number): string {
  const a0 = START + (fromScore / 100) * SWEEP
  const a1 = START + (toScore / 100) * SWEEP
  const [x0, y0] = polar(a0)
  const [x1, y1] = polar(a1)
  const large = a1 - a0 > 180 ? 1 : 0
  return `M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1}`
}

function toneForScore(score: number): string {
  if (score >= 60) return 'var(--good)'
  if (score >= 40) return 'var(--warn)'
  return 'var(--bad)'
}

export function FelGauge({ fel }: { fel: Fel }) {
  const tone = toneForScore(fel.score)
  const [nx, ny] = polar(START + (fel.score / 100) * SWEEP)

  return (
    <div className="gauge-wrap">
      <svg
        viewBox="0 0 180 150"
        width="100%"
        style={{ maxWidth: 230 }}
        role="img"
        aria-label={`FEL readiness score ${fel.score} out of 100, rated ${fel.band}.`}
      >
        {/* Track */}
        <path d={arcPath(0, 100)} fill="none" stroke="var(--surface-sunken)" strokeWidth="13" strokeLinecap="round" />
        {/* Value arc */}
        <path
          d={arcPath(0, Math.max(0.5, fel.score))}
          fill="none"
          stroke={tone}
          strokeWidth="13"
          strokeLinecap="round"
        />
        {/* Needle */}
        <line x1={CX} y1={CY} x2={nx} y2={ny} stroke="var(--navy)" strokeWidth="2.5" strokeLinecap="round" />
        <circle cx={CX} cy={CY} r="5" fill="var(--navy)" />
        {/* Readout */}
        <text x={CX} y={CY - 14} textAnchor="middle" fontSize="34" fontWeight="700" fill="var(--ink)" className="tnum">
          {fel.score}
        </text>
        <text x={CX} y={CY + 6} textAnchor="middle" fontSize="11" fill="var(--ink-faint)">
          / 100
        </text>
      </svg>

      <span className="gauge-band" style={{ background: 'transparent', color: tone, border: `1px solid ${tone}` }}>
        {fel.band}
      </span>

      <div className="fel-components" style={{ width: '100%' }}>
        {(Object.keys(COMPONENT_LABELS) as (keyof Fel['components'])[]).map((key) => (
          <div className="fel-component" key={key}>
            <div className="fel-component__top">
              <span className="fel-component__label">{COMPONENT_LABELS[key]}</span>
              <span className="fel-component__val tnum">{fel.components[key].toFixed(0)}</span>
            </div>
            <div className="meter">
              <div className="meter__fill" style={{ width: `${fel.components[key]}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
