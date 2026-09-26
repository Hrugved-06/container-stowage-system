import pandas as pd


try:
    from .constraints import check_all_constraints
except ImportError:
    from constraints import check_all_constraints

def calculate_assignment_rate(solution):

    if len(solution) == 0:
        return 0.0

    assigned = solution[
        "slot_id"
    ].notna().sum()

    return (
        assigned
        / len(solution)
        * 100
    )


def calculate_slot_utilization(
    solution,
    slots
):

    if len(slots) == 0:
        return 0.0

    used = solution[
        "slot_id"
    ].notna().sum()

    return (
        used
        / len(slots)
        * 100
    )


def calculate_total_loaded_weight(
    solution
):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    return float(
        assigned[
            "container_weight"
        ].sum()
    )


def calculate_average_container_weight(
    solution
):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return 0.0

    return float(
        assigned[
            "container_weight"
        ].mean()
    )


def calculate_teu(solution):

    assigned = solution[
        solution["slot_id"].notna()
    ]

    if assigned.empty:
        return 0

    return int(
        (
            assigned[
                "container_size"
            ] / 20
        ).sum()
    )


def verify_solution_constraints(
    solution,
    containers,
    slots
):

    container_lookup = (
        containers
        .set_index(
            "container_id"
        )
    )

    slot_lookup = (
        slots
        .set_index(
            "slot_id"
        )
    )

    violations = []

    assigned = solution[
        solution["slot_id"].notna()
    ]

    for _, assignment in assigned.iterrows():

        container = (
            container_lookup.loc[
                assignment[
                    "container_id"
                ]
            ]
        )

        slot = (
            slot_lookup.loc[
                assignment[
                    "slot_id"
                ]
            ]
        )

        result = check_all_constraints(
            container,
            slot
        )

        if not result["valid"]:

            violations.append(
                {
                    "container_id":
                        assignment[
                            "container_id"
                        ],

                    "slot_id":
                        assignment[
                            "slot_id"
                        ],

                    "constraints":
                        result
                }
            )

    return violations


def evaluate_solution(
    solution,
    containers,
    slots
):

    violations = (
        verify_solution_constraints(
            solution,
            containers,
            slots
        )
    )

    return {

        "assignment_rate":
            calculate_assignment_rate(
                solution
            ),

        "slot_utilization":
            calculate_slot_utilization(
                solution,
                slots
            ),

        "total_loaded_weight":
            calculate_total_loaded_weight(
                solution
            ),

        "average_container_weight":
            calculate_average_container_weight(
                solution
            ),

        "total_teu":
            calculate_teu(
                solution
            ),

        "constraint_violations":
            len(violations)
    }