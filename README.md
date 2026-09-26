# AI-Driven Container Vessel Cargo Scheduling and Voyage Planning System

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?style=for-the-badge&logo=vercel)](https://container-stowage-system.vercel.app/)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?style=for-the-badge&logo=react)
![Vite](https://img.shields.io/badge/Vite-Build-646CFF?style=for-the-badge&logo=vite)

## Live Application

**Try the deployed project here:**

https://container-stowage-system.vercel.app/

---

## Overview

The **AI-Driven Container Vessel Cargo Scheduling and Voyage Planning System** is a final-year engineering project designed to generate efficient container stowage plans for cargo vessels.

The current prototype focuses primarily on **container cargo scheduling and stowage optimization**. It evaluates container properties, vessel-slot restrictions, destination sequence, cargo priority, weight distribution and rehandling requirements to determine suitable container placements.

The system compares multiple optimization algorithms under the same dataset and constraint framework and produces a **Recommended Stowage Plan** showing where each selected container should be placed using **Bay–Row–Tier coordinates**.

The application supports both built-in realistic synthetic datasets and user-uploaded custom CSV datasets.

---

## Problem Statement

Container vessels may carry hundreds or thousands of containers with different:

- Sizes
- Weights
- Destination ports
- Priorities
- Refrigeration requirements
- Hazardous cargo restrictions

Improper container placement can lead to unnecessary rehandling at intermediate ports, poor weight distribution, slot incompatibility and inefficient cargo allocation.

This project develops an optimization framework that attempts to assign containers to compatible vessel slots while considering these operational constraints.

---

## Main Objectives

- Generate an optimized container stowage plan.
- Determine suitable **Bay, Row and Tier** positions for containers.
- Reduce unnecessary container rehandling.
- Improve vessel weight distribution.
- Respect container-slot compatibility constraints.
- Consider destination sequence while placing containers.
- Handle refrigerated and hazardous cargo restrictions.
- Prioritize important cargo when vessel capacity is limited.
- Compare multiple optimization techniques.
- Produce a clear recommended stowage plan.
- Allow users to upload their own datasets.
- Export optimization results in multiple formats.

---

## Key Features

### Intelligent Stowage Optimization

The system evaluates cargo and available vessel slots before generating container assignments.

Each result contains information such as:

- Container ID
- Container size
- Weight
- Destination
- Priority
- Bay
- Row
- Tier
- Assignment status

---

### Multiple Optimization Algorithms

The system contains seven optimization approaches:

1. Greedy
2. Priority Greedy
3. Best Fit
4. Randomized Greedy
5. Simulated Annealing
6. Genetic Algorithm
7. CP-SAT

All selected algorithms can be evaluated using the same dataset and constraint framework.

---

### Recommended Stowage Plan

After optimization, the application presents a recommended solution with important performance metrics such as:

- Assigned containers
- Unassigned containers
- Assignment rate
- Slot utilization
- Estimated rehandling
- Weight imbalance
- Constraint violations
- Objective score
- Computation time

---

## Custom Multi-CSV Dataset Support

Users are not limited to the datasets included with the project.

The application can accept **multiple CSV files in a single upload**.

For example:

```text
containers_mumbai.csv
containers_colombo.csv
containers_singapore.csv
vessel_slots.csv
```

The system attempts to automatically distinguish between:

- Container / cargo datasets
- Vessel / slot datasets

Multiple files belonging to the same category can be combined into a single optimization dataset.

---

## Smart CSV Preprocessing

Custom datasets do not need to use exactly the same column names as the built-in datasets.

For example, container identifiers may appear as:

```text
container_id
Container ID
container_no
container_number
cntr_id
```

Weight may appear as:

```text
weight
gross_weight
container_weight
mass
weight_kg
```

Destination may appear as:

```text
destination
destination_port
discharge_port
POD
port_of_discharge
```

The system also normalizes common Boolean representations including:

```text
True / False
Yes / No
Y / N
1 / 0
Allowed / Not Allowed
```

Where appropriate, safe defaults or derived values are used for certain missing optional fields.

Files that cannot be reliably identified as cargo or vessel-slot data are rejected with a readable validation message instead of producing misleading optimization results.

---

## Container Constraints

The system evaluates several container and slot compatibility rules.

### Size Compatibility

Containers must be assigned to compatible vessel slots.

Example:

```text
20 ft container → compatible slot
40 ft container → compatible 40 ft slot
```

---

### Weight Restrictions

A container cannot be placed in a slot whose maximum weight capacity is lower than the container weight.

---

### Refrigerated Containers

Refrigerated containers require slots that support reefer cargo.

---

### Hazardous Cargo

Hazardous containers can only be assigned to slots that permit hazardous cargo under the simplified academic model.

---

### Destination-Aware Placement

Destination sequence is considered during evaluation so containers intended for earlier discharge ports can be placed more accessibly where possible.

This helps reduce unnecessary rehandling at intermediate ports.

---

### Weight Distribution

The optimization framework evaluates how container weight is distributed across the simplified vessel layout.

This project models **weight-distribution balance** and does not claim to replace complete naval-architecture stability or ballast calculations.

---

## Built-in Test Scenarios

The project includes several synthetic operational scenarios.

| Dataset | Containers | Vessel Slots | Scenario |
|---|---:|---:|---|
| Demo | 12 | 12 | Basic demonstration |
| Small | 84 | 80 | Near-capacity / over-demand |
| Medium | 176 | 160 | Medium operational scenario |
| Large | 460 | 400 | Larger optimization challenge |

The larger datasets intentionally contain **more containers than available vessel slots**.

This means the optimizer must determine not only **where containers should be placed**, but also which containers should receive the available compatible positions when demand exceeds vessel capacity.

The datasets contain combinations of:

- 20 ft and 40 ft containers
- Multiple container weights
- Multiple discharge destinations
- Cargo priorities
- Refrigerated containers
- Hazardous cargo
- Different vessel-slot restrictions

> These datasets are realistic synthetic academic scenarios and are not claimed to be proprietary shipping-line manifests.

---

## Example Workflow

```text
Container / Cargo Dataset
          ↓
Custom Data Preprocessing
          ↓
Vessel Slot Configuration
          ↓
Constraint Validation
          ↓
Stowage Optimization
          ↓
Algorithm Comparison
          ↓
Recommended Stowage Plan
          ↓
Bay–Row–Tier Visualization
          ↓
Export Results
```

---

## Export Formats

Optimization results can be downloaded in multiple formats:

- CSV
- JSON
- Excel
- Microsoft Word
- PDF
- ZIP containing multiple result files

The exported reports can include:

- Optimization summary
- Algorithm comparison
- Recommended plan
- Container assignments
- Performance metrics

---

## Technology Stack

### Frontend

- React
- Vite
- JavaScript
- HTML
- CSS

### Backend

- Python
- FastAPI
- Uvicorn
- Pandas

### Optimization

- Greedy Algorithms
- Best-Fit Heuristics
- Simulated Annealing
- Genetic Algorithm
- Google OR-Tools CP-SAT

### Data Processing

- Pandas
- CSV processing
- Automatic field normalization
- Dataset validation

### Report Generation

- CSV
- JSON
- Excel
- Word
- PDF

### Deployment

- GitHub
- Vercel — Frontend
- Render-compatible FastAPI backend deployment

---

## System Architecture

```text
┌───────────────────────────┐
│        React / Vite       │
│        Frontend UI        │
└─────────────┬─────────────┘
              │
              │ HTTP / REST API
              ▼
┌───────────────────────────┐
│          FastAPI          │
│        Backend API        │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│     Dataset Processing    │
│ Validation / Cleaning /   │
│   Header Normalization    │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│   Optimization Framework  │
│                           │
│ Greedy                    │
│ Priority Greedy           │
│ Best Fit                  │
│ Randomized Greedy         │
│ Simulated Annealing       │
│ Genetic Algorithm         │
│ CP-SAT                    │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Evaluation & Constraints  │
│                           │
│ Rehandling                │
│ Weight Distribution       │
│ Priority                  │
│ Destination Sequence      │
│ Reefer / Hazardous Rules  │
└─────────────┬─────────────┘
              │
              ▼
┌───────────────────────────┐
│ Recommended Stowage Plan  │
│ Bay • Row • Tier          │
│ Metrics • Charts • Export │
└───────────────────────────┘
```

---

## Project Structure

```text
container-stowage-system/
│
├── backend/
│   └── FastAPI backend and API endpoints
│
├── frontend/
│   ├── src/
│   └── React / Vite user interface
│
├── optimization/
│   ├── optimization algorithms
│   ├── objective calculations
│   ├── constraints
│   └── evaluation logic
│
├── datasets/
│   └── Built-in container and vessel-slot datasets
│
├── experiments/
│   └── Experiment and benchmark-related files
│
├── requirements.txt
├── render.yaml
├── .python-version
├── .gitignore
└── README.md
```

---

## Run the Project Locally

### 1. Clone the Repository

```bash
git clone https://github.com/sameer8074/container-stowage-system
```

Move inside the project:

```bash
cd container-stowage-system
```

---

## Backend Setup

Create a Python virtual environment.

### Windows

```powershell
py -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the FastAPI backend:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The backend will normally run at:

```text
http://127.0.0.1:8000
```

---

## Frontend Setup

Open another terminal.

Move to the frontend directory:

```powershell
cd frontend
```

Install packages:

```powershell
npm install
```

Start Vite:

```powershell
npm run dev
```

Open the address displayed by Vite, normally:

```text
http://localhost:5173
```

---

## Production Environment

The frontend supports a production backend URL using:

```text
VITE_API_BASE_URL
```

Example:

```text
VITE_API_BASE_URL=https://your-backend-domain.com
```

For local development, the application can communicate with the locally running FastAPI server.

---


## Academic Scope

This project is an **academic prototype**.

The current implementation focuses on:

- Cargo scheduling
- Container allocation
- Container stowage optimization
- Destination-aware evaluation
- Constraint-based placement
- Algorithm comparison
- Weight-distribution evaluation

It should not be interpreted as a replacement for certified commercial vessel-loading software or professional naval-architecture systems.

---

## Future Scope

Possible future extensions include:

- Real-time vessel and AIS integration
- Live port schedules
- Weather-aware voyage routing
- Fuel-consumption optimization
- Detailed vessel stability calculations
- Ballast optimization
- Crane scheduling
- Dynamic rescheduling after operational disruptions
- Larger industrial datasets
- Real-time multi-port voyage optimization
- Reinforcement learning approaches
- Integration with shipping-line management systems

---

## Project Status

**Working final-year project prototype**

Current functionality includes:

- Built-in operational datasets
- Custom multi-file CSV upload
- Automatic dataset classification
- Dataset cleaning and normalization
- Constraint validation
- Seven optimization approaches
- Algorithm comparison
- Recommended stowage plan
- Bay–Row–Tier container placement
- Visualization
- Multi-format exports
- Live web deployment

---

## Live Demo

### [Open Container Stowage Optimization System](https://container-stowage-system.vercel.app/)

---

## Disclaimer

This application was developed for academic and research purposes.

The optimization rules and vessel representation are simplified compared with full commercial container-vessel planning systems. Actual vessel operations require additional structural, stability, lashing, dangerous-goods, regulatory and operational constraints.

---

## Authors

**Final Year Engineering Project**

Department of Information Technology  
Bharati Vidyapeeth College of Engineering, Navi Mumbai

---

## License

This repository is intended primarily for academic and educational use.
