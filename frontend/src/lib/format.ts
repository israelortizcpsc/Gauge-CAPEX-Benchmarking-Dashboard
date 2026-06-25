// Display formatting helpers, kept in one place so number formats stay
// consistent across KPIs, charts, and tables.

export function pct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function signedPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(digits)}%`
}

export function usdMillions(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}B`
  return `$${value.toFixed(0)}M`
}

export function num(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(digits)
}

// Ordinal-ish label for a percentile rank, e.g. 12.3 -> "12th percentile".
export function percentileLabel(rank: number): string {
  const rounded = Math.round(rank)
  const mod100 = rounded % 100
  const mod10 = rounded % 10
  let suffix = 'th'
  if (mod100 < 11 || mod100 > 13) {
    if (mod10 === 1) suffix = 'st'
    else if (mod10 === 2) suffix = 'nd'
    else if (mod10 === 3) suffix = 'rd'
  }
  return `${rounded}${suffix} percentile`
}
