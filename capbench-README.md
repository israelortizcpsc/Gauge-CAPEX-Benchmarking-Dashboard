<p align="center">
  <img src="docs/gauge-logo.svg" width="64" alt="Gauge logo" />
</p>

<h1 align="center">Gauge</h1>

<p align="center"><strong>A sustaining-CAPEX benchmarking dashboard.</strong></p>

<p align="center">
Enter a capital project and see where it sits against ~2,000 comparable ones —
cost-gap vs. P50/P80 norms, schedule predictability, an FEL-readiness score, and
a portfolio roll-up. Built on synthetic data, in React/TypeScript + Django/DRF.
</p>

<p align="center">
  <em>React 19 · TypeScript · Vite · Django 4.2 · Django REST Framework · 37 tests</em>
</p>

<p align="center">
  <strong><a href="https://israelortizcpsc.github.io/Gauge-CAPEX-Benchmarking-Dashboard/">▶ Live demo</a></strong>
</p>

> The live demo (GitHub Pages) runs the React app against a **frozen snapshot of
> the real Django API** — Pages can't host a backend, so the snapshot is exported
> from the actual endpoints (see `manage.py export_static`). The numbers are the
> genuine server-computed ones; only sector/project-type filters are wired in the
> hosted demo. Run locally (below) for the full live API and all filters.

---

> ⚠️ **All data is synthetic.** Gauge ships with ~2,000 procedurally generated
> projects. **No real client data is used anywhere.** The generator is shaped so
> the benchmarks behave realistically (better front-end loading → lower cost
> growth and schedule slip), which makes the dashboard meaningful without
> touching anything proprietary.

## Screenshots

| Portfolio + cost-gap benchmark | FEL readiness gauge |
| --- | --- |
| ![Dashboard](docs/screenshots/dashboard.png) | ![FEL gauge](docs/screenshots/fel.png) |

> _To capture these from the live app: run both servers (below), open
> `http://localhost:5173`, and screenshot into `docs/screenshots/`._

## What it does

- **Cost-gap benchmark.** For a selected project, compare three "higher-is-worse"
  metrics — capex intensity, cost growth, schedule slip — against its peer
  group's distribution (P10–P90 spread, P25–P75 box, **P50 median** and
  **P80 target** markers), with the project's percentile rank and its gap vs.
  the P50 norm and the P80 target.
- **FEL-readiness score.** A 0–100 Front-End Loading index rolled up from three
  1–5 sub-scores (scope definition, engineering maturity, execution planning),
  shown as a radial gauge with a readiness band (Best Practical → Screening).
- **Portfolio roll-up.** KPI strip over any filtered slice: project count, total
  capex, capex-weighted cost growth, median schedule slip, average FEL score,
  and % of projects over budget.
- **Peer-group filtering.** By sector, region, project type, and size band. The
  benchmark automatically **widens the peer group** when an exact slice is too
  thin to be statistically meaningful.
- **Shareable report.** "Export report" triggers a print-optimized layout
  (clean two-column, controls hidden) that saves to PDF from the browser.

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────────────┐
│  React + TypeScript      │  HTTP   │  Django REST Framework                │
│  (Vite)                  │ ──────▶ │                                       │
│                          │  /api   │  views ─ serializers (validate input) │
│  • FilterBar             │         │     │                                 │
│  • KpiStrip              │         │     ▼                                 │
│  • CostGapChart (SVG)    │ ◀────── │  services  (cache → aggregate → calc) │
│  • FelGauge (SVG)        │  JSON   │     │            │                    │
└─────────────────────────┘         │     ▼            ▼                    │
                                     │  stats.py    BenchmarkAggregate       │
                                     │  (pure math) (materialized cache)     │
                                     │                  │                    │
                                     │                  ▼                    │
                                     │             Project  (SQLite/Postgres)│
                                     └──────────────────────────────────────┘
```

### Key decisions (the defensible ones)

1. **All benchmark math lives server-side, in one pure module.**
   [`stats.py`](backend/benchmarks/stats.py) has no Django imports — just
   percentiles, ranks, cost gaps, and the FEL score. Every client that hits the
   API gets identical numbers (single source of truth), and the math is unit-
   testable in isolation. See [build notes](docs/BUILD_NOTES.md).

2. **Benchmark aggregates are pre-computed and cached by filter signature.**
   A peer group resolves _cache → materialized `BenchmarkAggregate` row →
   compute_. The signature is an order-independent encoding of the filters, so
   the same peer group always hits the same row and cache key. This keeps reads
   fast as the project count grows. See
   [`services.py`](backend/benchmarks/services.py).

3. **Inputs are validated at the serializer; reads are role-scoped.**
   Filter query params go through a DRF serializer with `ChoiceField`s before
   they ever reach the ORM. Projects flagged `is_confidential` are only visible
   to staff — anonymous/non-staff callers get a scoped queryset.

4. **Charts are accessible and responsive.** SVG/CSS charts carry `role="img"`
   with descriptive `aria-label`s and a visually-hidden data table fallback,
   honor `prefers-reduced-motion`, keep a visible keyboard focus ring, and
   reflow to a single column on mobile.

## API

| Method & path | Description |
| --- | --- |
| `GET /api/meta/` | Filter options + metric/FEL metadata for the UI |
| `GET /api/projects/` | List/filter/search/order projects (paginated) |
| `GET /api/projects/{id}/` | Project detail incl. derived metrics & FEL |
| `GET /api/projects/{id}/benchmark/` | Project vs. peer group: ranks, P50/P80 gaps, FEL |
| `GET /api/benchmarks/?sector=&region=&project_type=&size_band=` | Peer-group distributions |
| `GET /api/portfolio/?…` | Roll-up KPIs for a filtered slice |
| `GET /healthz` | Liveness probe |

Filters accepted by the benchmark/portfolio endpoints: `sector`, `region`,
`project_type`, `size_band` (all optional, validated against fixed choices).

## Running locally

### Backend (Django + DRF)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed              # ~2,000 synthetic projects + aggregates
python manage.py runserver         # http://127.0.0.1:8000
```

Seed options: `--count N`, `--clear`, `--seed N` (RNG seed for reproducibility).

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173  (proxies /api → :8000)
```

### Full stack via Docker

```bash
docker compose up --build          # Postgres + API on :8000 (seeds on first boot)
# then run the frontend with `npm run dev`
```

## Tests

```bash
cd backend
pytest                             # 37 tests
```

Coverage: the pure stats layer (percentile interpolation, ranks, cost gap, FEL
scoring & banding), the service layer (signatures, materialization, caching,
role scoping, peer-group widening), and the API (status codes, input
validation, confidential-read scoping).

```bash
cd frontend
npm run build                      # tsc type-check + production build
```

## Deployment

A [`render.yaml`](render.yaml) Blueprint provisions the API (Docker), a Postgres
database, and the static frontend together. The API container migrates and
seeds-if-empty on boot, serves via gunicorn, and ships static assets through
whitenoise. Production settings read everything from the environment
(`DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CORS_ALLOWED_ORIGINS`) and enable SSL/HSTS when `DJANGO_DEBUG=False`.

## Project layout

```
backend/
  gauge/                 # Django project (settings, urls, wsgi)
  benchmarks/
    models.py            # Project + materialized BenchmarkAggregate
    stats.py             # pure benchmark math (no Django) — the tested core
    services.py          # cache → aggregate → compute; per-project benchmark
    serializers.py       # read serializers + validated query params
    views.py             # read-only, role-scoped API
    management/commands/  # seed, seed_if_empty
    tests/               # stats / services / api
frontend/
  src/
    lib/api.ts           # typed API client
    components/          # FilterBar, KpiStrip, CostGapChart, FelGauge, Brand
    hooks/useAsync.ts    # request-cancelling data hook
docs/                    # build notes, screenshots
render.yaml              # deploy blueprint
docker-compose.yml       # local Postgres + API
```

## License

Synthetic demonstration project. MIT.
