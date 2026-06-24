In modern, minimalist design style, The signature project: CapBench, actually renamed to “Gauge”
A sustaining-CAPEX benchmarking dashboard: enter a project, see where it sits against ~2,000 comparable ones — cost-gap vs. P50/P80 norms, schedule predictability, an FEL-readiness score, portfolio roll-up, and a shareable report. Built on synthetic/public data, in React/TS + Django/DRF, deployed live.

This is deliberately a small, honest echo of InSite + FEL Toolbox. When the hiring manager opens it, the reaction you want is "this person already understands what we do." The full repo README is in capbench-README.md.
Why this specific project
It mirrors the actual job (internal/external data web apps) and their flagship product, so it doubles as domain proof.
It exercises every JD keyword: React/TS, Django, REST, data viz, performance (pre-computed aggregates), security (scoped reads, validated inputs), accessibility, Figma-to-code.
It's fully yours to defend — you can edit it live in an interview (see §8).
Scope it to what you can defend (pick ONE tier)
Tier A (48h): One page. Filter a seeded dataset; one cost-gap chart (project vs P50/P80); a single KPI strip. Django serves /api/projects + /api/benchmarks. Deployed. This alone beats 95% of applicants.
Tier B (multi-day): Add the FEL-readiness score, a portfolio roll-up view, and a print/PDF report export.
Tier C (stretch): Add CSV import so a user benchmarks their own portfolio, saved custom views, and confidence intervals on small slices.
Build notes (the defensible decisions)
Put the percentile/benchmark math server-side in Django so every client gets the same numbers. Be ready to explain why (single source of truth, testability).
Pre-compute/materialize benchmark aggregates, cache-keyed by filter signature → stays fast as data grows. (Performance is in the JD.)
Validate inputs at the DRF serializer; scope read endpoints by role. (Security is in the JD.)
Charts must be accessible (keyboard, labels, reduced-motion) and mobile-friendly (JD: "mobile-friendly applications").
Seed ~2,000 synthetic projects so benchmarks are meaningful. Never use real client data; say so in the README (already done).
Match IPA's restrained, corporate visual register — this is a tell that you read "maintain graphic standards and branding."
Definition of done
Live URL ✓ · public GitHub with real commit history + the README w/ images/gifs ✓ · a seed command ✓ · tests on the stats layer ✓ · a build write-up ✓.

