import io
import json
import os
import sys
import time
import uuid
from pathlib import Path

import pandas as pd

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# PROJECT PATH
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------
# OPTIMIZATION IMPORTS
# ---------------------------------------------------------

from optimization.algorithms import ALGORITHMS
from optimization.evaluation import evaluate_solution
from optimization.objective import calculate_objective_score

from backend.validator import validate_dataset
from backend.data_ingestion import ingest_files
from backend.exporter import create_exports


# ---------------------------------------------------------
# DIRECTORIES
# ---------------------------------------------------------

DATASET_DIR = PROJECT_ROOT / "datasets"
GENERATED_DIR = DATASET_DIR / "generated"
CUSTOM_DIR = DATASET_DIR / "custom"

RESULT_DIR = PROJECT_ROOT / "experiments" / "results"

GENERATED_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# FASTAPI
# ---------------------------------------------------------

app = FastAPI(
    title="AI-Assisted Container Stowage Planning API",
    description=(
        "Backend API for container stowage optimization, "
        "multi-objective evaluation and algorithm comparison."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

EXTRA_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=LOCAL_ORIGINS + EXTRA_ORIGINS,
    # Vercel production and preview URLs are accepted automatically.
    allow_origin_regex=r"https://[a-zA-Z0-9-]+\.vercel\.app",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# DATASET CONFIGURATION
# ---------------------------------------------------------

# These paths match the actual project structure:
#
# datasets/
# └── generated/
#     ├── containers.csv
#     ├── slots.csv
#     ├── small/
#     ├── medium/
#     └── large/

DATASETS = {
    "demo": {
        "name": "Demo",
        "description": "Training voyage scenario",
        "scenario": "Training voyage",
        "route": "JNPT (Mumbai) → Colombo → Port Klang → Singapore",
        "containers": GENERATED_DIR / "demo" / "containers.csv",
        "slots": GENERATED_DIR / "demo" / "slots.csv",
    },
    "small": {
        "name": "Small",
        "description": "Near-capacity feeder service",
        "scenario": "Peak feeder booking",
        "route": "JNPT (Mumbai) → Colombo → Port Klang → Singapore",
        "containers": GENERATED_DIR / "small" / "containers.csv",
        "slots": GENERATED_DIR / "small" / "slots.csv",
    },
    "medium": {
        "name": "Medium",
        "description": "Overbooked regional service",
        "scenario": "Regional peak-demand manifest",
        "route": "JNPT (Mumbai) → Colombo → Port Klang → Singapore",
        "containers": GENERATED_DIR / "medium" / "containers.csv",
        "slots": GENERATED_DIR / "medium" / "slots.csv",
    },
    "large": {
        "name": "Large",
        "description": "High-demand multi-port service",
        "scenario": "Congested multi-port manifest",
        "route": "JNPT (Mumbai) → Colombo → Port Klang → Singapore",
        "containers": GENERATED_DIR / "large" / "containers.csv",
        "slots": GENERATED_DIR / "large" / "slots.csv",
    },
    "custom": {
        "name": "Custom",
        "description": "User uploaded dataset",
        "scenario": "Custom uploaded manifest",
        "route": "Derived from uploaded destination order",
        "containers": CUSTOM_DIR / "containers.csv",
        "slots": CUSTOM_DIR / "slots.csv",
    },
}


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class OptimizationRequest(BaseModel):

    dataset: str = "demo"

    algorithms: list[str] = Field(
        default_factory=lambda: list(ALGORITHMS.keys())
    )


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def dataframe_records(df: pd.DataFrame):
    """Return strict JSON-safe records (no NaN/Infinity values)."""
    if df is None or df.empty:
        return []

    # pandas numeric columns keep NaN even after ``where(..., None)`` unless
    # converted to object first. Starlette intentionally rejects NaN in JSON.
    result = df.astype(object).where(pd.notna(df), None)
    records = result.to_dict(orient="records")

    cleaned = []
    for row in records:
        safe_row = {}
        for key, value in row.items():
            if value is None:
                safe_row[key] = None
                continue
            if hasattr(value, "item"):
                try:
                    value = value.item()
                except Exception:
                    pass
            if isinstance(value, float):
                import math
                safe_row[key] = value if math.isfinite(value) else None
            else:
                safe_row[key] = value
        cleaned.append(safe_row)
    return cleaned


def safe_number(value):
    if value is None:
        return None
    try:
        import math
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return value


def remove_custom_dataset():

    container_file = CUSTOM_DIR / "containers.csv"
    slot_file = CUSTOM_DIR / "slots.csv"

    for file in [container_file, slot_file]:

        try:
            if file.exists():
                file.unlink()
        except Exception:
            pass


def load_dataset(dataset_name: str):

    if dataset_name not in DATASETS:

        raise HTTPException(
            status_code=400,
            detail=f"Unknown dataset: {dataset_name}",
        )

    config = DATASETS[dataset_name]

    container_file = config["containers"]
    slot_file = config["slots"]

    if not container_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Container dataset not found: "
                f"{container_file}"
            ),
        )

    if not slot_file.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Slot dataset not found: "
                f"{slot_file}"
            ),
        )

    try:

        containers = pd.read_csv(
            container_file
        )

        slots = pd.read_csv(
            slot_file
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Could not read dataset: {error}",
        )

    validation = validate_dataset(
        containers,
        slots
    )

    if not validation["valid"]:

        raise HTTPException(
            status_code=400,
            detail=validation,
        )

    return containers, slots


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

@app.get("/")
def root():

    return {
        "name": "AI-Assisted Container Stowage Planning API",
        "version": "1.0.0",
        "status": "running",
    }


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "service": "container-stowage-api",
    }


# ---------------------------------------------------------
# DATASETS
# ---------------------------------------------------------

@app.get("/api/datasets")
def get_datasets():

    response = []

    for key in [
        "demo",
        "small",
        "medium",
        "large",
    ]:

        config = DATASETS[key]

        container_file = config["containers"]
        slot_file = config["slots"]

        if (
            container_file.exists()
            and slot_file.exists()
        ):

            try:

                containers = pd.read_csv(
                    container_file
                )

                slots = pd.read_csv(
                    slot_file
                )

                validation = validate_dataset(
                    containers,
                    slots
                )

                response.append({
                    "id": key,
                    "name": config["name"],
                    "description": config["description"],
                    "scenario": config.get("scenario", ""),
                    "route": config.get("route", ""),
                    "containers": len(containers),
                    "slots": len(slots),
                    "demand_ratio": round(len(containers) / len(slots), 3) if len(slots) else None,
                    "available": validation["valid"],
                })

            except Exception:

                response.append({
                    "id": key,
                    "name": config["name"],
                    "description": config["description"],
                    "scenario": config.get("scenario", ""),
                    "route": config.get("route", ""),
                    "containers": 0,
                    "slots": 0,
                    "demand_ratio": None,
                    "available": False,
                })

        else:

            response.append({
                "id": key,
                "name": config["name"],
                "description": config["description"],
                "containers": 0,
                "slots": 0,
                "available": False,
            })


    # -----------------------------------------------------
    # CUSTOM DATASET
    # -----------------------------------------------------

    custom_container = (
        CUSTOM_DIR / "containers.csv"
    )

    custom_slots = (
        CUSTOM_DIR / "slots.csv"
    )

    custom_available = False
    custom_containers = 0
    custom_slot_count = 0

    if (
        custom_container.exists()
        and custom_slots.exists()
    ):

        try:

            containers = pd.read_csv(
                custom_container
            )

            slots = pd.read_csv(
                custom_slots
            )

            validation = validate_dataset(
                containers,
                slots
            )

            if validation["valid"]:

                custom_available = True
                custom_containers = len(
                    containers
                )
                custom_slot_count = len(
                    slots
                )

        except Exception:

            custom_available = False


    response.append({
        "id": "custom",
        "name": "Custom",
        "description": "Uploaded manifest",
        "scenario": "Custom uploaded manifest",
        "route": "Derived from uploaded destination order",
        "containers": custom_containers,
        "slots": custom_slot_count,
        "demand_ratio": round(custom_containers / custom_slot_count, 3) if custom_slot_count else None,
        "available": custom_available,
    })


    return response


# ---------------------------------------------------------
# DATASET PREVIEW
# ---------------------------------------------------------

@app.get("/api/datasets/{dataset_name}")
def get_dataset(dataset_name: str):

    containers, slots = load_dataset(
        dataset_name
    )

    config = DATASETS[dataset_name]

    return {
        "dataset": dataset_name,
        "scenario": config.get("scenario", ""),
        "route": config.get("route", ""),
        "containers": len(containers),
        "slots": len(slots),

        "container_columns": list(
            containers.columns
        ),

        "slot_columns": list(
            slots.columns
        ),

        "container_preview": dataframe_records(
            containers.head(20)
        ),

        "slot_preview": dataframe_records(
            slots.head(20)
        ),
    }


# ---------------------------------------------------------
# CUSTOM CSV UPLOAD
# ---------------------------------------------------------

@app.post("/api/upload")
async def upload_dataset(files: list[UploadFile] = File(...)):
    """Smart multi-CSV importer.

    Users may upload 2 or more CSV files in any order. The importer detects
    container/cargo versus vessel-slot data, normalizes common column aliases,
    cleans common value formats and merges multiple files of the same type.
    """
    if len(files) < 2:
        raise HTTPException(status_code=400, detail={"message": "Upload at least two CSV files: container/cargo data and vessel slot data."})
    items = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail={"message": f"{file.filename or 'Selected file'} is not a CSV file."})
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail={"message": f"{file.filename} is empty."})
        items.append((file.filename, raw))
    try:
        containers, slots, reports, warnings = ingest_files(items)
    except ValueError as error:
        raise HTTPException(status_code=400, detail={"message": str(error)})
    validation = validate_dataset(containers, slots)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"message": "The files were recognized and cleaned, but the normalized dataset is still invalid.", **validation})
    container_path = CUSTOM_DIR / "containers.csv"
    slot_path = CUSTOM_DIR / "slots.csv"
    containers.to_csv(container_path, index=False)
    slots.to_csv(slot_path, index=False)
    metadata = {
        "dataset_id": "custom",
        "name": "Custom Dataset",
        "validation_status": "valid",
        "container_count": len(containers),
        "slot_count": len(slots),
        "files_processed": len(files),
        "file_reports": reports,
        "warnings": warnings,
    }
    (CUSTOM_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"message": "Custom dataset is ready.", "dataset": "custom", "containers": len(containers), "slots": len(slots), **metadata, **validation}


# ---------------------------------------------------------
# OPTIMIZATION
# ---------------------------------------------------------

@app.post("/api/optimize")
def optimize(
    request: OptimizationRequest
):

    # -----------------------------------------------------
    # LOAD DATASET
    # -----------------------------------------------------

    containers, slots = load_dataset(
        request.dataset
    )


    # -----------------------------------------------------
    # VALIDATE ALGORITHMS
    # -----------------------------------------------------

    if not request.algorithms:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Select at least one algorithm."
                )
            }
        )


    unknown = [
        algorithm
        for algorithm in request.algorithms
        if algorithm not in ALGORITHMS
    ]


    if unknown:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unknown algorithm.",
                "unknown": unknown,
                "available": list(
                    ALGORITHMS.keys()
                ),
            }
        )


    # -----------------------------------------------------
    # RUN OPTIMIZATION
    # -----------------------------------------------------

    run_id = str(
        uuid.uuid4()
    )

    started_all = time.perf_counter()

    comparison = []
    solutions = {}


    for algorithm_name in request.algorithms:

        algorithm = ALGORITHMS[
            algorithm_name
        ]

        start = time.perf_counter()


        try:

            solution = algorithm(
                containers,
                slots
            )

            runtime = (
                time.perf_counter()
                - start
            )


            if not isinstance(
                solution,
                pd.DataFrame
            ):

                raise TypeError(
                    "Algorithm must return pandas.DataFrame."
                )


            metrics = evaluate_solution(
                solution,
                containers,
                slots
            )


            objective = (
                calculate_objective_score(
                    solution
                )
            )


            solution_file = (
                RESULT_DIR
                / f"{run_id}_{algorithm_name}_solution.csv"
            )


            solution.to_csv(
                solution_file,
                index=False
            )


            row = {

                "algorithm":
                    algorithm_name,

                "status":
                    "SUCCESS",

                "runtime_seconds":
                    round(runtime, 6),

                "assignment_rate":
                    safe_number(
                        metrics["assignment_rate"]
                    ),

                "slot_utilization":
                    safe_number(
                        metrics["slot_utilization"]
                    ),

                "total_loaded_weight":
                    safe_number(
                        metrics["total_loaded_weight"]
                    ),

                "average_container_weight":
                    safe_number(
                        metrics["average_container_weight"]
                    ),

                "total_teu":
                    safe_number(
                        metrics["total_teu"]
                    ),

                "constraint_violations":
                    safe_number(
                        metrics["constraint_violations"]
                    ),

                "rehandling":
                    safe_number(
                        objective["rehandling"]
                    ),

                "weight_imbalance_std":
                    safe_number(
                        objective[
                            "weight_imbalance_std"
                        ]
                    ),

                "longitudinal_balance_error":
                    safe_number(
                        objective[
                            "longitudinal_balance_error"
                        ]
                    ),

                "destination_mixing":
                    safe_number(
                        objective[
                            "destination_mixing"
                        ]
                    ),

                "priority_penalty":
                    safe_number(
                        objective[
                            "priority_penalty"
                        ]
                    ),

                "unassigned":
                    safe_number(
                        objective[
                            "unassigned_containers"
                        ]
                    ),

                "objective_score":
                    safe_number(
                        objective[
                            "objective_score"
                        ]
                    ),

                "solution_file":
                    str(
                        solution_file.relative_to(
                            PROJECT_ROOT
                        )
                    ),
            }


            comparison.append(row)


            solutions[algorithm_name] = solution.copy()


        except Exception as error:

            runtime = (
                time.perf_counter()
                - start
            )


            comparison.append({

                "algorithm":
                    algorithm_name,

                "status":
                    "FAILED",

                "runtime_seconds":
                    round(runtime, 6),

                "error":
                    str(error),
            })


    # -----------------------------------------------------
    # SAVE COMPARISON + USER EXPORTS
    # -----------------------------------------------------

    comparison_file = RESULT_DIR / f"{run_id}_algorithm_comparison.csv"
    comparison_df = pd.DataFrame(comparison)
    comparison_df.to_csv(comparison_file, index=False)

    total_runtime = time.perf_counter() - started_all
    config = DATASETS[request.dataset]
    scenario = {
        "scenario": config.get("scenario", ""),
        "route": config.get("route", ""),
    }

    export_files_abs, recommended_algorithm, export_errors = create_exports(
        result_dir=RESULT_DIR,
        run_id=run_id,
        dataset_name=request.dataset,
        scenario=scenario,
        comparison=comparison,
        solutions=solutions,
        container_count=len(containers),
        slot_count=len(slots),
        total_runtime=round(total_runtime, 6),
    )

    export_files = {
        key: str(Path(path).resolve().relative_to(PROJECT_ROOT.resolve()))
        for key, path in export_files_abs.items()
    }
    export_files["comparison_csv"] = str(comparison_file.relative_to(PROJECT_ROOT))

    return {
        "run_id": run_id,
        "dataset": request.dataset,
        "scenario": scenario,
        "container_count": len(containers),
        "slot_count": len(slots),
        "demand_ratio": round(len(containers) / len(slots), 3) if len(slots) else None,
        "total_runtime_seconds": round(total_runtime, 6),
        "comparison": comparison,
        "recommended_algorithm": recommended_algorithm,
        "solutions": {
            name: dataframe_records(solution)
            for name, solution in solutions.items()
        },
        "export_files": export_files,
        "export_errors": export_errors,
    }


# ---------------------------------------------------------
# DOWNLOAD FILE
# ---------------------------------------------------------

@app.get("/api/download/{filename:path}")
def download_file(filename: str):

    requested_file = (
        PROJECT_ROOT / filename
    ).resolve()


    try:

        requested_file.relative_to(
            RESULT_DIR.resolve()
        )

    except ValueError:

        raise HTTPException(
            status_code=403,
            detail="Invalid file location."
        )


    if not requested_file.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found."
        )


    return FileResponse(
        requested_file
    )