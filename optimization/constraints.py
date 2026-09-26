import pandas as pd


def check_size_compatibility(container, slot):
    return int(container["size"]) == int(slot["size"])


def check_weight_compatibility(container, slot):
    return float(container["weight"]) <= float(slot["max_weight"])


def check_refrigerated_compatibility(container, slot):
    refrigerated = bool(container["refrigerated"])
    reefer_capable = bool(slot["reefer_capable"])

    if refrigerated:
        return reefer_capable

    return True


def check_hazardous_compatibility(container, slot):
    hazardous = bool(container["hazardous"])
    allowed = bool(slot["hazardous_allowed"])

    if hazardous:
        return allowed

    return True


def check_all_constraints(container, slot):

    results = {
        "size": check_size_compatibility(container, slot),
        "weight": check_weight_compatibility(container, slot),
        "refrigerated": check_refrigerated_compatibility(
            container,
            slot
        ),
        "hazardous": check_hazardous_compatibility(
            container,
            slot
        ),
    }

    results["valid"] = all(results.values())

    return results


def is_valid_placement(container, slot):
    return check_all_constraints(
        container,
        slot
    )["valid"]


def get_constraint_violation_count(container, slot):

    results = check_all_constraints(
        container,
        slot
    )

    return sum(
        1
        for key, value in results.items()
        if key != "valid" and not value
    )


if __name__ == "__main__":

    containers = pd.read_csv(
        "datasets/generated/containers.csv"
    )

    slots = pd.read_csv(
        "datasets/generated/slots.csv"
    )

    container = containers.iloc[0]
    slot = slots.iloc[0]

    results = check_all_constraints(
        container,
        slot
    )

    print("\n===== CONSTRAINT TEST =====")

    print("Container:", container["container_id"])
    print("Slot:", slot["slot_id"])

    for name, result in results.items():
        print(f"{name}: {result}")