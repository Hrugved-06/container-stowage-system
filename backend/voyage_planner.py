from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api",
    tags=["Voyage Planning"],
)


# ============================================================
# ACADEMIC ROUTE DATA
# ============================================================
#
# These are configurable approximate sailing distances.
# They are used for academic voyage-planning demonstration,
# not for certified maritime navigation.
#
# Distance unit: nautical miles (NM)
# ============================================================

LEG_DISTANCE_NM = {
    ("jnpt", "colombo"): 890.0,
    ("colombo", "port klang"): 1390.0,
    ("port klang", "singapore"): 190.0,
}


PORT_DISPLAY_NAMES = {
    "jnpt": "JNPT (Mumbai)",
    "colombo": "Colombo",
    "port klang": "Port Klang",
    "singapore": "Singapore",
}


PORT_ALIASES = {
    "jnpt": "jnpt",
    "jnpt (mumbai)": "jnpt",
    "jawaharlal nehru port": "jnpt",
    "nhava sheva": "jnpt",
    "mumbai": "jnpt",

    "colombo": "colombo",
    "port of colombo": "colombo",

    "port klang": "port klang",
    "portklang": "port klang",
    "klang": "port klang",

    "singapore": "singapore",
    "port of singapore": "singapore",
}


# ============================================================
# REQUEST MODEL
# ============================================================

class VoyagePlanRequest(BaseModel):
    route: str | list[str]

    plan: list[dict[str, Any]]

    vessel_speed_knots: float = Field(
        default=18.0,
        gt=0
    )

    fuel_consumption_tpd: float = Field(
        default=45.0,
        ge=0
    )

    port_stay_hours: float = Field(
        default=8.0,
        ge=0
    )

    # Configurable academic emission factor:
    # tonnes CO2 per tonne of fuel.
    emission_factor: float = Field(
        default=3.114,
        ge=0
    )

    departure_time: str | None = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_port(port: str) -> str:
    value = str(port).strip().lower()

    return PORT_ALIASES.get(
        value,
        value
    )


def display_port(port: str) -> str:
    normalized = normalize_port(port)

    return PORT_DISPLAY_NAMES.get(
        normalized,
        str(port).strip()
    )


def parse_route(route: str | list[str]) -> list[str]:
    if isinstance(route, list):
        ports = [
            str(port).strip()
            for port in route
            if str(port).strip()
        ]

    else:
        route_text = str(route)

        # Support common route separators.
        route_text = route_text.replace(
            "->",
            "→"
        )

        route_text = route_text.replace(
            "=>",
            "→"
        )

        ports = [
            part.strip()
            for part in route_text.split("→")
            if part.strip()
        ]

    if len(ports) < 2:
        raise HTTPException(
            status_code=400,
            detail=(
                "Voyage route must contain at least "
                "two ports."
            )
        )

    return ports


def get_departure_time(
    departure_time: str | None
) -> datetime:

    if not departure_time:
        return datetime.now().replace(
            microsecond=0
        )

    try:
        cleaned = departure_time.replace(
            "Z",
            "+00:00"
        )

        return datetime.fromisoformat(
            cleaned
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid departure_time. "
                "Use ISO format such as "
                "2026-10-01T08:00:00."
            )
        ) from exc


def container_is_assigned(
    container: dict[str, Any]
) -> bool:

    assigned = container.get(
        "assigned"
    )

    if isinstance(assigned, bool):
        return assigned

    slot_id = (
        container.get("slot_id")
        or container.get("slotId")
    )

    if slot_id is None:
        return False

    value = str(slot_id).strip().lower()

    return value not in {
        "",
        "none",
        "null",
        "n/a",
    }


def container_destination(
    container: dict[str, Any]
) -> str:

    return normalize_port(
        container.get(
            "destination",
            ""
        )
    )


def container_weight(
    container: dict[str, Any]
) -> float:

    value = (
        container.get(
            "container_weight"
        )
        or container.get(
            "weight"
        )
        or 0
    )

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return 0.0


def get_priority_level(
    container: dict[str, Any]
) -> str:

    level = container.get(
        "priority_level"
    )

    if level:
        return str(level).strip().title()

    return "Normal"


def get_leg_distance(
    from_port: str,
    to_port: str
) -> float:

    source = normalize_port(
        from_port
    )

    destination = normalize_port(
        to_port
    )

    direct_key = (
        source,
        destination
    )

    reverse_key = (
        destination,
        source
    )

    if direct_key in LEG_DISTANCE_NM:
        return LEG_DISTANCE_NM[
            direct_key
        ]

    if reverse_key in LEG_DISTANCE_NM:
        return LEG_DISTANCE_NM[
            reverse_key
        ]

    raise HTTPException(
        status_code=400,
        detail=(
            "No academic sailing-distance "
            f"configuration exists for "
            f"{display_port(source)} → "
            f"{display_port(destination)}."
        )
    )


# ============================================================
# VOYAGE GENERATOR
# ============================================================

def build_voyage_plan(
    request: VoyagePlanRequest
) -> dict[str, Any]:

    ports = parse_route(
        request.route
    )

    normalized_ports = [
        normalize_port(port)
        for port in ports
    ]

    departure_time = (
        get_departure_time(
            request.departure_time
        )
    )

    # Only assigned containers are considered
    # part of the vessel's final stowage plan.
    scheduled_containers = [
        container
        for container in request.plan
        if container_is_assigned(
            container
        )
    ]

    total_containers = len(
        request.plan
    )

    scheduled_count = len(
        scheduled_containers
    )

    unscheduled_count = (
        total_containers
        - scheduled_count
    )

    current_time = departure_time

    legs = []

    total_distance_nm = 0.0
    total_sailing_hours = 0.0
    total_port_hours = 0.0

    # --------------------------------------------------------
    # Generate each voyage leg
    # --------------------------------------------------------

    for index in range(
        len(normalized_ports) - 1
    ):

        from_port = (
            normalized_ports[
                index
            ]
        )

        to_port = (
            normalized_ports[
                index + 1
            ]
        )

        distance_nm = (
            get_leg_distance(
                from_port,
                to_port
            )
        )

        sailing_hours = (
            distance_nm
            / request.vessel_speed_knots
        )

        estimated_arrival = (
            current_time
            + timedelta(
                hours=sailing_hours
            )
        )

        # Containers discharged at
        # destination port.
        discharge_containers = [
            container
            for container
            in scheduled_containers
            if container_destination(
                container
            ) == to_port
        ]

        discharge_count = len(
            discharge_containers
        )

        discharge_weight = sum(
            container_weight(
                container
            )
            for container
            in discharge_containers
        )

        priority_counter = Counter(
            get_priority_level(
                container
            )
            for container
            in discharge_containers
        )

        is_final_port = (
            index ==
            len(
                normalized_ports
            ) - 2
        )

        # For presentation, we count port stay
        # at each destination port.
        stay_hours = (
            request.port_stay_hours
        )

        departure_from_port = (
            estimated_arrival
            + timedelta(
                hours=stay_hours
            )
        )

        leg = {
            "sequence": index + 1,

            "from_port":
                display_port(
                    from_port
                ),

            "to_port":
                display_port(
                    to_port
                ),

            "distance_nm":
                round(
                    distance_nm,
                    2
                ),

            "vessel_speed_knots":
                round(
                    request.vessel_speed_knots,
                    2
                ),

            "sailing_hours":
                round(
                    sailing_hours,
                    2
                ),

            "estimated_arrival":
                estimated_arrival.isoformat(),

            "port_stay_hours":
                round(
                    stay_hours,
                    2
                ),

            "estimated_departure":
                (
                    None
                    if is_final_port
                    else departure_from_port.isoformat()
                ),

            "containers_to_discharge":
                discharge_count,

            "discharge_weight":
                round(
                    discharge_weight,
                    2
                ),

            "priority_breakdown":
                dict(
                    priority_counter
                ),
        }

        legs.append(
            leg
        )

        total_distance_nm += (
            distance_nm
        )

        total_sailing_hours += (
            sailing_hours
        )

        total_port_hours += (
            stay_hours
        )

        current_time = (
            departure_from_port
        )

    # ========================================================
    # FUEL ESTIMATION
    # ========================================================

    sailing_days = (
        total_sailing_hours
        / 24.0
    )

    estimated_fuel_tonnes = (
        sailing_days
        * request.fuel_consumption_tpd
    )

    estimated_co2_tonnes = (
        estimated_fuel_tonnes
        * request.emission_factor
    )

    total_voyage_hours = (
        total_sailing_hours
        + total_port_hours
    )

    final_arrival = (
        legs[-1][
            "estimated_arrival"
        ]
        if legs
        else None
    )

    # ========================================================
    # PORT CARGO SUMMARY
    # ========================================================

    port_cargo = []

    for sequence, port in enumerate(
        normalized_ports
    ):

        if sequence == 0:

            port_cargo.append(
                {
                    "port":
                        display_port(
                            port
                        ),

                    "sequence": 0,

                    "operation":
                        "Loading / Departure",

                    "containers":
                        scheduled_count,

                    "cargo_weight":
                        round(
                            sum(
                                container_weight(
                                    container
                                )
                                for container
                                in scheduled_containers
                            ),
                            2
                        ),
                }
            )

            continue

        containers_here = [
            container
            for container
            in scheduled_containers
            if container_destination(
                container
            ) == port
        ]

        port_cargo.append(
            {
                "port":
                    display_port(
                        port
                    ),

                "sequence":
                    sequence,

                "operation":
                    "Discharge",

                "containers":
                    len(
                        containers_here
                    ),

                "cargo_weight":
                    round(
                        sum(
                            container_weight(
                                container
                            )
                            for container
                            in containers_here
                        ),
                        2
                    ),
            }
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    return {
        "status":
            "SUCCESS",

        "route": [
            display_port(
                port
            )
            for port
            in normalized_ports
        ],

        "route_text":
            " → ".join(
                display_port(
                    port
                )
                for port
                in normalized_ports
            ),

        "departure_time":
            departure_time.isoformat(),

        "final_arrival":
            final_arrival,

        "summary": {
            "total_containers":
                total_containers,

            "scheduled_containers":
                scheduled_count,

            "unscheduled_containers":
                unscheduled_count,

            "total_distance_nm":
                round(
                    total_distance_nm,
                    2
                ),

            "total_sailing_hours":
                round(
                    total_sailing_hours,
                    2
                ),

            "total_sailing_days":
                round(
                    sailing_days,
                    2
                ),

            "total_port_stay_hours":
                round(
                    total_port_hours,
                    2
                ),

            "estimated_total_voyage_hours":
                round(
                    total_voyage_hours,
                    2
                ),

            "estimated_total_voyage_days":
                round(
                    total_voyage_hours
                    / 24.0,
                    2
                ),

            "estimated_sailing_fuel_tonnes":
                round(
                    estimated_fuel_tonnes,
                    2
                ),

            "estimated_co2_tonnes":
                round(
                    estimated_co2_tonnes,
                    2
                ),
        },

        "vessel_parameters": {
            "speed_knots":
                request.vessel_speed_knots,

            "fuel_consumption_tpd":
                request.fuel_consumption_tpd,

            "port_stay_hours":
                request.port_stay_hours,

            "emission_factor":
                request.emission_factor,
        },

        "legs":
            legs,

        "port_cargo":
            port_cargo,

        "methodology_note": (
            "This module provides an academic "
            "voyage-planning estimate using a "
            "predefined port sequence, configurable "
            "sailing distances, vessel speed, port "
            "stay time, optimized container "
            "assignments and destination information. "
            "It is not a certified maritime "
            "navigation or naval-stability system."
        ),
    }


# ============================================================
# API ENDPOINT
# ============================================================

@router.post(
    "/voyage-plan"
)
def create_voyage_plan(
    request: VoyagePlanRequest
):

    return build_voyage_plan(
        request
    )