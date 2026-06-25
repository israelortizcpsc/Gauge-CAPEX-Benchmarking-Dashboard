// The Gauge wordmark + a small gauge/dial glyph — the visual signature.

export function GaugeMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 36 36" role="img" aria-label="Gauge logo">
      <circle cx="18" cy="18" r="16" fill="none" stroke="var(--line-strong)" strokeWidth="2" />
      {/* Sweep arc from ~210° to ~-30° representing the dial scale. */}
      <path
        d="M 8.1 27.9 A 14 14 0 1 1 27.9 27.9"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      {/* Needle pointing to ~upper-right (a 'good' reading). */}
      <line x1="18" y1="18" x2="25" y2="11.5" stroke="var(--navy)" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="18" cy="18" r="2.6" fill="var(--navy)" />
    </svg>
  )
}

export function Brand() {
  return (
    <div className="brand">
      <GaugeMark className="brand__mark" />
      <div>
        <div className="brand__name">Gauge</div>
        <div className="brand__tag">Sustaining-CAPEX Benchmarking</div>
      </div>
    </div>
  )
}
