# How I built Gauge — and where I drew the line with AI

![Gauge dashboard](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/dashboard.png)

> A short, honest write-up of what Gauge is, why it exists, and how I worked with
> AI to build it without losing ownership of the parts that matter.

**Live demo:** [israelortizcpsc.github.io/Gauge-CAPEX-Benchmarking-Dashboard](https://israelortizcpsc.github.io/Gauge-CAPEX-Benchmarking-Dashboard/) ·
**Code:** [GitHub](https://github.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard)

> Hosted on GitHub Pages against a frozen snapshot of the Django API (Pages is
> static-only). The numbers are the server's; clone to run the live backend.

---

## The problem

Sustaining capital — the unglamorous, recurring spend that keeps an existing
plant, mine, or refinery running — is where a lot of money quietly leaks. These
projects rarely get the front-end rigor that a marquee greenfield expansion
does, and they overrun for boring, repeatable reasons: scope that wasn't fixed
at sanction, engineering that wasn't mature enough, an execution plan that didn't
exist yet. The tell shows up *after* the money's spent, as cost growth against
the sanctioned budget and schedule slip against the plan.

The hard part isn't knowing a single project overran. It's knowing whether a
**+9% cost growth is good or bad for a project like this one** — same sector,
same size, same type of work. Without a peer set, every number is just a number.
That's the question Gauge answers: drop a project onto its peer distribution and
show where it actually sits.

## What I built

A one-page benchmarking dashboard on ~2,000 synthetic sustaining-capital
projects (no real client data — the generator is shaped so the benchmarks behave
realistically, e.g. better front-end loading really does predict lower overrun).

**Pick a peer group, and the whole portfolio re-benchmarks live:**

![Filtering the peer group](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/filter.gif)

**Pick a project, and you see exactly where it lands** — its capex intensity,
cost growth, and schedule slip against the peer P10–P90 spread, with the **P50
median** and **P80 "competitive target"** marked, plus an FEL-readiness gauge
scoring how well the project was defined at sanction:

![Benchmarking individual projects](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/project.gif)

The stack is **React + TypeScript (Vite)** on the front and **Django + Django
REST Framework** on the back, with the benchmark math computed server-side and
materialized into a filter-keyed cache. See **[[Architecture and Decisions]]**
for the trade-offs.

## Where AI helped

I used an AI coding agent throughout, and it genuinely earned its place:

- **Scaffolding.** Standing up the Django project, the DRF viewset/serializer
  wiring, the Vite app, env-driven settings, the Dockerfile and Render
  blueprint — boilerplate I've written a dozen times. Letting AI type it meant I
  spent my time on the model and the math instead of `startproject`.
- **Tests.** It drafted the bulk of the 37-test suite. I directed *what* to test
  (percentile edge cases, role-scoped reads, peer-group widening) and reviewed
  every assertion, but the typing-out was AI.
- **Rubber-ducking the percentile math.** I wanted the percentile function to
  agree with what an analyst would get from NumPy or Excel, not a hand-rolled
  approximation that's subtly off. Talking through the interpolation method — and
  pinning it with tests against NumPy's default `linear` method — was faster as a
  dialogue than alone.

## Where I drew the line

The things that make this *my* project, I own:

- **The data model is mine.** What a `Project` is, which dimensions define a peer
  group (sector / region / type / size band), why cost is normalized to an
  *intensity* before it's compared, why the FEL score weights scope above
  engineering above execution — those are domain decisions, not code decisions.
- **The stats layer is mine.** Everything in `stats.py` — percentiles,
  percentile rank with a midpoint tie convention, the cost-gap definition, the
  FEL roll-up. It's deliberately framework-free so it's the part that's easiest
  to reason about and hardest to fake understanding of.
- **The architecture is mine.** Computing benchmarks *server-side* for a single
  source of truth, materializing aggregates keyed by an order-independent filter
  signature, widening the peer group when a slice is too thin — the load-bearing
  choices, each of which I can defend.

My rule: **if I couldn't explain a line, I rewrote it until I could.**

## One thing it got wrong that I caught

The most useful bug never showed up as a failing test in isolation — which is
exactly why it's worth telling.

The benchmark service caches peer-group results in Django's in-process cache. The
AI's test suite passed when I ran tests one at a time. Run the *whole* file, and a
service test started failing: it expected a freshly-seeded peer group of **2
projects** but got **20**.

The cause: `pytest-django` wraps each test in a database transaction and rolls it
back, so the *database* is clean between tests — but **`LocMemCache` is not part
of that transaction.** An earlier test had materialized a `sector=mining`
aggregate with 20 projects and left it in the cache. The next test, with its own
2 projects, asked for `sector=mining`, got a cache hit, and read the *previous*
test's stale answer. The AI had quietly assumed the cache rolled back like the
DB. It doesn't.

The fix is small — an autouse fixture that clears the cache around every test:

```python
@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()
```

But catching it required knowing the difference between *what Django's test
transaction covers* (the DB) and *what it doesn't* (a separate cache backend) —
and noticing that "passes alone, fails together" is the classic signature of
shared mutable state leaking across tests. That's the line I care about: not that
the AI wrote a bug, but that I could read its code well enough to know *why* it
was wrong before trusting it.

*(A sibling gotcha from the same build: the seed command uses `bulk_create` for
speed, which **bypasses `Model.save()`** — so the `size_band` field I compute in
`save()` would have been blank on all 2,000 rows, silently breaking the size
filter. I set it explicitly before the bulk insert. Same lesson: know what the
shortcut skips.)*

---

In 2026 the interesting question isn't "did you use AI?" — everyone does. It's
"do you understand what it gave you?" Gauge is my answer: a project I can open in
front of you and change live, where the parts that matter are parts I can derive.
