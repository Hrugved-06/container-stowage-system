import random
import math
import time

import pandas as pd

try:
    from .constraints import check_all_constraints
    from .objective import calculate_objective_score
except ImportError:
    from constraints import check_all_constraints
    from objective import calculate_objective_score


def empty_assignment(container):

    return {
        "container_id": container["container_id"],
        "slot_id": None,
        "bay": None,
        "row": None,
        "tier": None,
        "container_size": container["size"],
        "container_weight": container["weight"],
        "destination": container["destination"],
        "destination_order": container.get(
            "destination_order",
            999
        ),
        "priority": container["priority"],
        "hazardous": container["hazardous"],
        "refrigerated": container["refrigerated"],
    }


def make_assignment(container, slot):

    return {
        "container_id": container["container_id"],
        "slot_id": slot["slot_id"],
        "bay": slot["bay"],
        "row": slot["row"],
        "tier": slot["tier"],
        "container_size": container["size"],
        "container_weight": container["weight"],
        "destination": container["destination"],
        "destination_order": container.get(
            "destination_order",
            999
        ),
        "priority": container["priority"],
        "hazardous": container["hazardous"],
        "refrigerated": container["refrigerated"],
    }


def greedy(
    containers,
    slots,
    ordering=None
):

    if ordering is None:
        ordered = containers.copy()
    else:
        ordered = containers.loc[
            ordering
        ]

    assignments = []

    occupied = set()

    for _, container in ordered.iterrows():

        placed = False

        for _, slot in slots.iterrows():

            if slot["slot_id"] in occupied:
                continue

            result = check_all_constraints(
                container,
                slot
            )

            if result["valid"]:

                assignments.append(
                    make_assignment(
                        container,
                        slot
                    )
                )

                occupied.add(
                    slot["slot_id"]
                )

                placed = True

                break

        if not placed:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


def priority_greedy(
    containers,
    slots
):

    ordering = (
        containers
        .sort_values(
            [
                "priority",
                "destination_order",
                "weight"
            ],
            ascending=[
                True,
                True,
                False
            ]
        )
        .index
    )

    return greedy(
        containers,
        slots,
        ordering
    )


def best_fit(
    containers,
    slots
):

    assignments = []

    occupied = set()

    for _, container in containers.iterrows():

        candidates = []

        for _, slot in slots.iterrows():

            if slot["slot_id"] in occupied:
                continue

            result = check_all_constraints(
                container,
                slot
            )

            if not result["valid"]:
                continue

            remaining_capacity = (
                float(slot["max_weight"])
                - float(container["weight"])
            )

            size_difference = abs(
                int(slot["size"])
                - int(container["size"])
            )

            score = (
                size_difference * 100000
                + remaining_capacity
            )

            candidates.append(
                (
                    score,
                    slot
                )
            )

        if candidates:

            candidates.sort(
                key=lambda x: x[0]
            )

            _, selected = candidates[0]

            assignments.append(
                make_assignment(
                    container,
                    selected
                )
            )

            occupied.add(
                selected["slot_id"]
            )

        else:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


def randomized_greedy(
    containers,
    slots,
    seed=42
):

    rng = random.Random(
        seed
    )

    ordered = list(
        containers.index
    )

    rng.shuffle(
        ordered
    )

    return greedy(
        containers,
        slots,
        ordered
    )


def random_neighbor(
    solution,
    containers,
    slots,
    rng
):

    candidate = solution.copy()

    assigned_rows = candidate[
        candidate["slot_id"].notna()
    ].index.tolist()

    if not assigned_rows:
        return candidate

    row_index = rng.choice(
        assigned_rows
    )

    container_id = candidate.loc[
        row_index,
        "container_id"
    ]

    container = containers[
        containers["container_id"]
        == container_id
    ].iloc[0]

    available = slots[
        ~slots["slot_id"].isin(
            candidate["slot_id"].dropna()
        )
    ]

    valid = []

    for _, slot in available.iterrows():

        if check_all_constraints(
            container,
            slot
        )["valid"]:

            valid.append(
                slot
            )

    if not valid:
        return candidate

    selected = rng.choice(
        valid
    )

    candidate.loc[
        row_index,
        [
            "slot_id",
            "bay",
            "row",
            "tier"
        ]
    ] = [
        selected["slot_id"],
        selected["bay"],
        selected["row"],
        selected["tier"]
    ]

    return candidate


def simulated_annealing(
    containers,
    slots,
    iterations=3000,
    initial_temperature=1000.0,
    cooling=0.995,
    seed=42
):

    rng = random.Random(
        seed
    )

    current = randomized_greedy(
        containers,
        slots,
        seed
    )

    current_score = calculate_objective_score(
        current
    )["objective_score"]

    best = current.copy()

    best_score = current_score

    temperature = initial_temperature

    for _ in range(iterations):

        candidate = random_neighbor(
            current,
            containers,
            slots,
            rng
        )

        candidate_score = calculate_objective_score(
            candidate
        )["objective_score"]

        delta = (
            candidate_score
            - current_score
        )

        if (
            delta < 0
            or rng.random()
            <
            math.exp(
                -delta
                / max(
                    temperature,
                    1e-9
                )
            )
        ):

            current = candidate
            current_score = candidate_score

        if current_score < best_score:

            best = current.copy()

            best_score = current_score

        temperature *= cooling

    return best


def genetic_algorithm(
    containers,
    slots,
    population_size=30,
    generations=100,
    mutation_rate=0.10,
    seed=42
):

    rng = random.Random(
        seed
    )

    population = []

    for i in range(
        population_size
    ):

        population.append(
            randomized_greedy(
                containers,
                slots,
                seed + i
            )
        )

    def fitness(solution):

        return calculate_objective_score(
            solution
        )["objective_score"]

    for _ in range(
        generations
    ):

        population.sort(
            key=fitness
        )

        elite = population[
            :max(
                2,
                population_size // 5
            )
        ]

        new_population = [
            x.copy()
            for x in elite
        ]

        while len(
            new_population
        ) < population_size:

            parent = rng.choice(
                elite
            )

            child = parent.copy()

            if rng.random() < mutation_rate:

                child = random_neighbor(
                    child,
                    containers,
                    slots,
                    rng
                )

            new_population.append(
                child
            )

        population = new_population

    population.sort(
        key=fitness
    )

    return population[0]


def cp_sat(
    containers,
    slots,
    time_limit=30
):

    from ortools.sat.python import cp_model

    model = cp_model.CpModel()

    variables = {}

    for i, container in containers.iterrows():

        for j, slot in slots.iterrows():

            if check_all_constraints(
                container,
                slot
            )["valid"]:

                variables[
                    (i, j)
                ] = model.NewBoolVar(
                    f"x_{i}_{j}"
                )

    for i in containers.index:

        possible = [
            variables[(i, j)]
            for j in slots.index
            if (i, j) in variables
        ]

        if possible:

            model.Add(
                sum(possible) <= 1
            )

    for j in slots.index:

        possible = [
            variables[(i, j)]
            for i in containers.index
            if (i, j) in variables
        ]

        if possible:

            model.Add(
                sum(possible) <= 1
            )

    objective_terms = []

    for (i, j), variable in variables.items():

        priority = int(
            containers.loc[
                i,
                "priority"
            ]
        )

        objective_terms.append(
            (1000 - priority)
            * variable
        )

    model.Maximize(
        sum(objective_terms)
    )

    solver = cp_model.CpSolver()

    solver.parameters.max_time_in_seconds = (
        time_limit
    )

    status = solver.Solve(
        model
    )

    assignments = []

    used_containers = set()

    for (i, j), variable in variables.items():

        if solver.Value(
            variable
        ) == 1:

            container = containers.loc[
                i
            ]

            slot = slots.loc[
                j
            ]

            assignments.append(
                make_assignment(
                    container,
                    slot
                )
            )

            used_containers.add(
                i
            )

    for i, container in containers.iterrows():

        if i not in used_containers:

            assignments.append(
                empty_assignment(
                    container
                )
            )

    return pd.DataFrame(
        assignments
    )


ALGORITHMS = {

    "greedy": greedy,

    "priority_greedy":
        priority_greedy,

    "best_fit":
        best_fit,

    "randomized_greedy":
        randomized_greedy,

    "simulated_annealing":
        simulated_annealing,

    "genetic":
        genetic_algorithm,

    "cp_sat":
        cp_sat
}