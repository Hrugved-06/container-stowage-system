import pandas as pd

try:
    from .constraints import check_all_constraints
except ImportError:
    from constraints import check_all_constraints


def greedy_stowage(containers, slots):
    """
    Assign containers to the first available slot
    that satisfies all constraints.

    This is our baseline greedy algorithm.
    """

    assignments = []

    occupied_slots = set()

    for _, container in containers.iterrows():

        assigned = False

        for _, slot in slots.iterrows():

            slot_id = slot["slot_id"]

            # Skip slots that are already occupied
            if slot_id in occupied_slots:
                continue

            # Check whether the container can use this slot
            constraint_results = check_all_constraints(
                container,
                slot
            )

            if constraint_results["valid"]:

                assignments.append(
                    {
                        "container_id": container["container_id"],
                        "slot_id": slot_id,
                        "bay": slot["bay"],
                        "row": slot["row"],
                        "tier": slot["tier"],
                        "container_size": container["size"],
                        "container_weight": container["weight"],
                        "destination": container["destination"],
                        "priority": container["priority"],
                    }
                )

                occupied_slots.add(slot_id)

                assigned = True

                break

        # If no valid slot was found
        if not assigned:

            assignments.append(
                {
                    "container_id": container["container_id"],
                    "slot_id": None,
                    "bay": None,
                    "row": None,
                    "tier": None,
                    "container_size": container["size"],
                    "container_weight": container["weight"],
                    "destination": container["destination"],
                    "priority": container["priority"],
                }
            )

    return pd.DataFrame(assignments)


if __name__ == "__main__":

    # Load generated datasets
    containers = pd.read_csv(
        "datasets/generated/containers.csv"
    )

    slots = pd.read_csv(
        "datasets/generated/slots.csv"
    )

    # Run greedy algorithm
    result = greedy_stowage(
        containers,
        slots
    )

    print("\n===== GREEDY STOWAGE PLAN =====\n")

    print(
        result.to_string(index=False)
    )
    
    result.to_csv(
        "experiments/results/greedy_solution.csv",
        index=False
    )

    # Count assigned containers
    assigned = result["slot_id"].notna().sum()

    unassigned = result["slot_id"].isna().sum()

    print("\n===== SUMMARY =====")

    print(
        "Total containers:",
        len(containers)
    )

    print(
        "Assigned containers:",
        assigned
    )

    print(
        "Unassigned containers:",
        unassigned
    )

    print(
        "Used slots:",
        assigned
    )

    print(
        "Available slots:",
        len(slots)
    )