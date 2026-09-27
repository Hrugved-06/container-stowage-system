# AI-Driven Container Vessel Cargo Scheduling and Voyage Planning System

Final-year project prototype for intelligent container stowage planning. The system accepts built-in or custom CSV datasets, validates and normalizes cargo/slot data, runs multiple optimization algorithms, compares results, recommends a stowage plan, visualizes assignments, and exports reports in multiple formats.

## Main Features

- React + Vite frontend
- FastAPI backend
- Built-in realistic synthetic benchmark datasets
- Multi-file custom CSV upload with automatic container/slot detection
- Header/value normalization and safe defaults for incomplete datasets
- Seven optimization approaches: Greedy, Priority Greedy, Best Fit, Randomized Greedy, Simulated Annealing, Genetic Algorithm, and CP-SAT
- Size, weight, reefer, hazardous, priority, destination/rehandling, and weight-distribution considerations
- Recommended stowage plan with Bay / Row / Tier placement
- CSV, JSON, Excel, Word, PDF, and ZIP exports

## Local Run

### Backend

```bash
py -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`.

## Deployment

Recommended simple deployment:

- Backend: Render Web Service
- Frontend: Vercel

### Render backend

Use repository root as the service root.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`

A `render.yaml` file is included for convenience.

### Vercel frontend

Import the same GitHub repository and set the Vercel **Root Directory** to `frontend`.

Add environment variable:

```text
VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com
```

Then redeploy the frontend.

## Academic Scope

This prototype focuses on cargo scheduling and container stowage optimization. It does not claim to implement full commercial naval-stability analysis, ballast optimization, crane scheduling, live AIS routing, or weather-routing systems.

## Deployment Note

Custom uploaded datasets and generated reports are stored on the backend service's local runtime filesystem. On hosts with ephemeral filesystems such as a free Render service, these runtime files can disappear after a restart or redeployment. Built-in datasets remain part of the repository.

## Public Benchmark / Research Reproducibility

For research evaluation, the repository now includes an **RCSPPSuite-derived benchmark mode** in addition to the original controlled synthetic datasets.

Three deterministic reduced datasets are generated from public RCSPPSuite source instances:

| Dataset | Source instance | Containers | Adapted positions |
|---|---|---:|---:|
| RCSPPSuite Small | `s_01` | 84 | 80 |
| RCSPPSuite Medium | `m_01` | 176 | 160 |
| RCSPPSuite Large | `l_01` | 460 | 400 |

Rebuild them with:

```bash
python datasets/rcspp_adapter.py
```

The generated `manifest.json` files record source instance IDs, vessel profiles, seeds, field mappings, preserved attributes and excluded constraints.

For repeatable research experiments:

```bash
python research/run_rcspp_benchmark.py --dataset rcspp_small --repeats 5
```

or:

```bash
python research/run_rcspp_benchmark.py --dataset all --repeats 5
```

### Benchmark scope

The RCSPPSuite mode is deliberately described as **RCSPPSuite-derived / adapted**, not as full RCSPP compliance. The present B.E. prototype models container/slot compatibility, weight limits, reefer requirements, cargo priority, destination order, rehandling-oriented metrics and simplified weight distribution. Full RCSPP hydrostatics, ballast, GM, bending moment, lashing, crane constraints, paired block stowage, exact two-half 40-foot occupancy and dynamic arrival-condition evolution remain outside the current model.

See `research/RCSPP_BENCHMARK_PROTOCOL.md` for the exact reproducibility and paper wording.
