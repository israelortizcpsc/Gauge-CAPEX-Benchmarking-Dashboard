# Gauge — Sustaining-CAPEX Benchmarking

Enter a capital project and see where it sits against ~2,000 comparable ones:
cost-gap vs. P50/P80 norms, schedule predictability, an FEL-readiness score, and
a portfolio roll-up. **React/TypeScript + Django/DRF, on synthetic data.**

![Gauge dashboard](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/dashboard.png)

## Pages in this wiki

- **[[How This Was Built]]** — the problem, what I built, where AI helped, where
  I drew the line, and one bug I caught. Start here.
- **[[Architecture and Decisions]]** — the engineering trade-offs: server-side
  math, materialized aggregates, role-scoped reads, accessibility.

## Quick links

- **Code:** [main repository](https://github.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard)
- **Full README:** [capbench-README.md](https://github.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/blob/main/capbench-README.md)
- **Live demo:** _<!-- paste Render URL when deployed -->_

## In one screen

| Filter the peer group | Benchmark a project |
| --- | --- |
| ![Filtering](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/filter.gif) | ![Benchmarking](https://raw.githubusercontent.com/israelortizcpsc/Gauge-CAPEX-Benchmarking-Dashboard/main/docs/screenshots/project.gif) |

> All data is synthetic — ~2,000 procedurally generated projects. No real client
> data is used anywhere.
