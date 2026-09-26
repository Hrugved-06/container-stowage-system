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
