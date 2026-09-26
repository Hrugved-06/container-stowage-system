import io
import json
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
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
        "description": "Small demonstration dataset",
        "containers": GENERATED_DIR / "containers.csv",
        "slots": GENERATED_DIR / "slots.csv",
    },

    "small": {
        "name": "Small",
        "description": "Small benchmark dataset",
        "containers": GENERATED_DIR / "small" / "containers.csv",
        "slots": GENERATED_DIR / "small" / "slots.csv",
    },

    "medium": {
        "name": "Medium",
        "description": "Medium benchmark dataset",
        "containers": GENERATED_DIR / "medium" / "containers.csv",
        "slots": GENERATED_DIR / "medium" / "slots.csv",
    },

    "large": {
        "name": "Large",
        "description": "Large benchmark dataset",
        "containers": GENERATED_DIR / "large" / "containers.csv",
        "slots": GENERATED_DIR / "large" / "slots.csv",
    },

    "custom": {
        "name": "Custom",
        "description": "User uploaded dataset",
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

    result = df.copy()

    result = result.where(
        pd.notna(result),
        None
    )

    return result.to_dict(
        orient="records"
    )


def safe_number(value):

    if value is None:
        return None

    try:
        return float(value)
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
                    "containers": len(containers),
                    "slots": len(slots),
                    "available": validation["valid"],
                })

            except Exception:

                response.append({
                    "id": key,
                    "name": config["name"],
                    "description": config["description"],
                    "containers": 0,
                    "slots": 0,
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
        "description": (
            "Upload your own container and slot CSV files"
        ),
        "containers": custom_containers,
        "slots": custom_slot_count,
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

    return {
        "dataset": dataset_name,
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
async def upload_dataset(
    containers_file: UploadFile = File(...),
    slots_file: UploadFile = File(...),
):

    # -----------------------------------------------------
    # BASIC FILE CHECK
    # -----------------------------------------------------

    if not containers_file.filename:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Container CSV file was not selected."
            }
        )

    if not slots_file.filename:

        raise HTTPException(
            status_code=400,
            detail={
                "message": "Slot CSV file was not selected."
            }
        )


    if not containers_file.filename.lower().endswith(
        ".csv"
    ):

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Container data must be uploaded "
                    "as a CSV file."
                )
            }
        )


    if not slots_file.filename.lower().endswith(
        ".csv"
    ):

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Slot data must be uploaded "
                    "as a CSV file."
                )
            }
        )


    # -----------------------------------------------------
    # READ FILES WITHOUT SAVING THEM FIRST
    # -----------------------------------------------------

    container_bytes = (
        await containers_file.read()
    )

    slot_bytes = (
        await slots_file.read()
    )


    # -----------------------------------------------------
    # PARSE CSV
    # -----------------------------------------------------

    try:

        containers = pd.read_csv(
            io.BytesIO(container_bytes)
        )

        slots = pd.read_csv(
            io.BytesIO(slot_bytes)
        )

    except Exception as error:

        # Remove any previous custom dataset so that
        # an invalid upload cannot leave stale data.

        remove_custom_dataset()

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    f"Could not read the uploaded CSV files: "
                    f"{error}"
                )
            }
        )


    # -----------------------------------------------------
    # VALIDATE DATASET
    # -----------------------------------------------------

    validation = validate_dataset(
        containers,
        slots
    )


    if not validation["valid"]:

        # IMPORTANT:
        # Do not keep the previous custom dataset.
        remove_custom_dataset()

        raise HTTPException(
            status_code=400,
            detail=validation
        )


    # -----------------------------------------------------
    # ONLY SAVE AFTER SUCCESSFUL VALIDATION
    # -----------------------------------------------------

    container_path = (
        CUSTOM_DIR / "containers.csv"
    )

    slot_path = (
        CUSTOM_DIR / "slots.csv"
    )

    container_path.write_bytes(
        container_bytes
    )

    slot_path.write_bytes(
        slot_bytes
    )


    return {
        "message": (
            "Custom dataset uploaded and validated successfully."
        ),

        "dataset": "custom",

        "containers": len(containers),

        "slots": len(slots),

        "container_columns": list(
            containers.columns
        ),

        "slot_columns": list(
            slots.columns
        ),

        **validation,
    }


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


            solutions[
                algorithm_name
            ] = dataframe_records(
                solution
            )


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
    # SAVE COMPARISON
    # -----------------------------------------------------

    comparison_file = (
        RESULT_DIR
        / f"{run_id}_algorithm_comparison.csv"
    )

    comparison_json = (
        RESULT_DIR
        / f"{run_id}_algorithm_comparison.json"
    )


    comparison_df = pd.DataFrame(
        comparison
    )


    comparison_df.to_csv(
        comparison_file,
        index=False
    )


    with open(
        comparison_json,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            comparison,
            file,
            indent=4
        )


    total_runtime = (
        time.perf_counter()
        - started_all
    )


    return {

        "run_id":
            run_id,

        "dataset":
            request.dataset,

        "container_count":
            len(containers),

        "slot_count":
            len(slots),

        "total_runtime_seconds":
            round(
                total_runtime,
                6
            ),

        "comparison":
            comparison,

        "solutions":
            solutions,

        "export_files": {

            "csv":
                str(
                    comparison_file.relative_to(
                        PROJECT_ROOT
                    )
                ),

            "json":
                str(
                    comparison_json.relative_to(
                        PROJECT_ROOT
                    )
                ),
        },
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