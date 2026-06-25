# Build notes

Why Gauge is built the way it is — the decisions I'd defend in a review.

## 1. Benchmark math is server-side and framework-free

Every number a user sees — percentiles, ranks, cost gaps, the FEL score — is
computed in [`backend/benchmarks/stats.py`](../backend/benchmarks/stats.py),
which imports nothing from Django. Two reasons:

- **Single source of truth.** If the percentile math lived in the React client,
  a second client (a mobile app, an export job, a partner integration) could
  drift. Putting it behind the API guarantees identical figures everywhere.
- **Testability.** Pure functions over plain lists are trivial to unit-test
  exhaustively without spinning up a database or a request. The percentile
  implementation is checked against NumPy's default linear-interpolation method
  so the behavior is a known quantity, not a bespoke approximation.

The model layer exposes derived metrics as Python properties
(`cost_growth`, `schedule_slip`, `capex_intensity`, `fel`) that delegate to
`stats.py`. Derived values are **never stored as truth** — they're computed from
the raw inputs, so there's no denormalized field to fall out of sync.

## 2. Pre-computed aggregates, keyed by a filter signature

Benchmarks are read far more often than the underlying data changes, and a
naive implementation recomputes percentiles over the whole peer group on every
request. Instead:

```
request → make_signature(filters) → cache.get → BenchmarkAggregate row → compute
```

- `make_signature` produces a **canonical, order-independent** key, so
  `{sector: mining, region: europe}` and `{region: europe, sector: mining}`
  resolve to the same row and cache entry. Empty/None filters are dropped.
- On a miss, the peer group is scanned **once** and every metric summarized,
  then the row is written to `BenchmarkAggregate` and the cache.
- `seed` materializes the common views (all projects, each single sector, each
  single project type) up front. The full filter cross-product is *not*
  enumerated — it grows combinatorially and most cells are empty — so rarer
  combinations are computed and cached lazily on first request.

This is the "performance via pre-computed aggregates" point from the brief, made
concrete. It stays fast as the project count grows because hot reads never touch
project rows.

## 3. Validate at the boundary, scope reads by role

- **Validation.** Filter query strings hit a DRF `Serializer` with `ChoiceField`s
  (`BenchmarkQuerySerializer`) before anything reaches the ORM. An unknown
  sector is a clean `400`, not a silent empty result or an injection surface.
- **Role scoping.** Projects can be flagged `is_confidential`. The view builds a
  **scoped base queryset** — non-staff callers never see confidential rows, in
  the list, the detail, the benchmark, or the portfolio roll-up. Scoped reads
  are cached under a separate namespace so they can't leak into the public
  aggregate table. There's a test asserting an anonymous caller's peer count
  differs from staff's.

## 4. Small-slice handling

A $400M mega-project in a thin sector/region/type/size cell has too few peers to
benchmark honestly. `project_benchmark` **widens the peer group** through a
fallback chain (exact → sector+type → sector → all) until it has a defensible
sample (≥12), and the response flags whether the match was exact so the UI can
say so ("peer group widened for a robust sample"). This is an honest answer to
the confidence-on-small-slices problem rather than reporting a percentile off
three data points.

## 5. Accessibility and responsiveness as defaults

- Charts are SVG/CSS with `role="img"` and descriptive `aria-label`s; the
  cost-gap chart also renders a visually-hidden `<table>` of the same numbers
  for screen readers and no-CSS contexts.
- A global `prefers-reduced-motion` rule collapses animation/transition
  durations; a consistent `:focus-visible` ring keeps keyboard navigation legible.
- The layout reflows from a two-column desktop grid to a single column on
  mobile, and the KPI strip from six columns to two.
- A `@media print` block turns the dashboard into a clean report (controls and
  the picker hidden, shadows removed, content kept from breaking across pages).

## 6. Synthetic data, shaped to be realistic

The seed generator ([`seed.py`](../backend/benchmarks/management/commands/seed.py))
uses a fixed RNG seed for reproducibility and encodes real relationships:
sectors have distinct cost intensities; better FEL maturity drives lower
expected cost growth and schedule slip; project types scale cost differently;
and everything carries lognormal/Gaussian noise. The result is a dataset where
the benchmarks tell a coherent story — without using a single real data point.

## Trade-offs / what I'd do next

- **In-process cache.** `LocMemCache` is per-process; behind multiple gunicorn
  workers each warms its own. For real scale this would move to Redis (one line
  in settings). The materialized table is the durable layer regardless.
- **Aggregate freshness.** Aggregates are rebuilt on seed. In a system with live
  writes I'd invalidate by signature on project change (or run a periodic
  rebuild) rather than trusting the TTL alone.
- **Auth.** Role scoping is demonstrated via Django's staff flag; a real
  deployment would put token/SSO auth in front and map org membership to scopes.
- **Tier C.** CSV import (benchmark your own portfolio) and saved custom views
  are the natural next features; the service layer already accepts an arbitrary
  scoped queryset, so user-uploaded sets would slot in without reshaping the core.
```
