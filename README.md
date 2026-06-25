# Gauge — Sustaining-CAPEX Benchmarking Dashboard

Enter a capital project and see where it sits against ~2,000 comparable ones:
cost-gap vs. P50/P80 norms, schedule predictability, an FEL-readiness score, and
a portfolio roll-up. **React/TypeScript + Django/DRF, on synthetic data.**

📖 **Full documentation, architecture, and run instructions:
[`capbench-README.md`](capbench-README.md)**
🛠️ **Build write-up (the defensible decisions): [`docs/BUILD_NOTES.md`](docs/BUILD_NOTES.md)**

## Quick start

```bash
# Backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed && python manage.py runserver

# Frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

```bash
cd backend && pytest    # 37 tests on the stats, service, and API layers
```

> All data is synthetic — ~2,000 procedurally generated projects. No real client
> data is used anywhere.
