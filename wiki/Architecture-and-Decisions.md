# Architecture & decisions

Why Gauge is built the way it is — the decisions I'd defend in a review.
For the narrative version see **[[How This Was Built]]**.

```
┌─────────────────────────┐         ┌──────────────────────────────────────┐
│  React + TypeScript      │  HTTP   │  Django REST Framework                │
│  (Vite)                  │ ──────▶ │                                       │
│  • FilterBar             │  /api   │  views ─ serializers (validate input) │
│  • KpiStrip              │         │     │                                 │
│  • CostGapChart (SVG)    │ ◀────── │  services (cache → aggregate → calc)  │
│  • FelGauge (SVG)        │  JSON   │     │            │                    │
└─────────────────────────┘         │  stats.py    BenchmarkAggregate       │
                                     │  (pure math) (materialized cache)     │
                                     │                  │                    │
                                     │             Project  (SQLite/Postgres)│
                                     └──────────────────────────────────────┘
```

## 1. Benchmark math is server-side and framework-free

Every number a user sees — percentiles, ranks, cost gaps, the FEL score — is
computed in `stats.py`, which imports nothing from Django.

- **Single source of truth.** If the percentile math lived in the React client,
  a second client (mobile app, export job, partner integration) could drift.
  Behind the API, every client gets identical figures.
- **Testability.** Pure functions over plain lists are trivial to unit-test
  without a database or a request. The percentile implementation is checked
  against NumPy's default linear-interpolation method, so the behavior is a known
  quantity, not a bespoke approximation.

Derived values (`cost_growth`, `schedule_slip`, `capex_intensity`, `fel`) are
model **properties** computed from raw inputs — never stored as truth, so there's
no denormalized field to fall out of sync.

## 2. Pre-computed aggregates, keyed by a filter signature

Benchmarks are read far more often than the data changes, and recomputing
percentiles over a whole peer group on every request doesn't scale. Instead:

```
request → make_signature(filters) → cache.get → BenchmarkAggregate row → compute
```

- `make_signature` is **canonical and order-independent**, so
  `{sector: mining, region: europe}` and `{region: europe, sector: mining}`
  resolve to the same row and cache entry. Empty filters are dropped.
- On a miss, the peer group is scanned **once**, every metric summarized, then
  written to the table and the cache.
- `seed` materializes the common views (all projects, each single sector, each
  single type) up front. The full filter cross-product is *not* enumerated — it
  grows combinatorially and most cells are empty — so rarer combinations are
  computed and cached lazily on first request.

## 3. Validate at the boundary, scope reads by role

- **Validation.** Filter query strings hit a DRF serializer with `ChoiceField`s
  before anything reaches the ORM. An unknown sector is a clean `400`, not a
  silent empty result or an injection surface.
- **Role scoping.** Projects can be flagged `is_confidential`. The view builds a
  scoped base queryset — non-staff callers never see confidential rows in the
  list, detail, benchmark, or portfolio roll-up. Scoped reads are cached under a
  separate namespace so they can't leak into the public aggregate table.

## 4. Small-slice handling

A mega-project in a thin sector/region/type/size cell has too few peers to
benchmark honestly. `project_benchmark` **widens the peer group** through a
fallback chain (exact → sector+type → sector → all) until it has a defensible
sample (≥12), and flags whether the match was exact so the UI can say so. An
honest answer to the confidence-on-small-slices problem rather than a percentile
off three data points.

## 5. Accessibility & responsiveness as defaults

- SVG/CSS charts carry `role="img"` with descriptive `aria-label`s; the cost-gap
  chart also renders a visually-hidden `<table>` of the same numbers.
- A global `prefers-reduced-motion` rule collapses animation; a consistent
  `:focus-visible` ring keeps keyboard navigation legible.
- Two-column desktop grid reflows to one column on mobile; the KPI strip goes
  six → two. A `@media print` block turns the dashboard into a clean PDF report.

## Trade-offs / what's next

- **In-process cache.** `LocMemCache` is per-process; behind multiple gunicorn
  workers each warms its own. At real scale this moves to Redis (one line). The
  materialized table is the durable layer regardless.
- **Aggregate freshness.** Rebuilt on seed today; with live writes I'd invalidate
  by signature on change or run a periodic rebuild rather than trust the TTL.
- **Auth.** Role scoping uses Django's staff flag; production would front it with
  token/SSO auth mapping org membership to scopes.
- **Next features.** CSV import (benchmark your own portfolio) and saved views —
  the service layer already accepts an arbitrary scoped queryset, so uploaded
  sets slot in without reshaping the core.
