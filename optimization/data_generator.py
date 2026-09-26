import pandas as pd


def generate_containers():
    """
    Generate sample container data for our stowage planning system.
    """

    containers = [
        {
            "container_id": "C001",
            "size": 20,
            "weight": 12000,
            "destination": "Mumbai",
            "priority": 1,
            "hazardous": False,
            "refrigerated": False,
        },
        {
            "container_id": "C002",
            "size": 40,
            "weight": 22000,
            "destination": "Dubai",
            "priority": 2,
            "hazardous": False,
            "refrigerated": False,
        },
        {
            "container_id": "C003",
            "size": 20,
            "weight": 15000,
            "destination": "Singapore",
            "priority": 1,
            "hazardous": False,
            "refrigerated": True,
        },
        {
            "container_id": "C004",
            "size": 40,
            "weight": 28000,
            "destination": "Colombo",
            "priority": 3,
            "hazardous": True,
            "refrigerated": False,
        },
        {
            "container_id": "C005",
            "size": 20,
            "weight": 10000,
            "destination": "Dubai",
            "priority": 2,
            "hazardous": False,
            "refrigerated": False,
        },
        {
            "container_id": "C006",
            "size": 40,
            "weight": 25000,
            "destination": "Singapore",
            "priority": 1,
            "hazardous": False,
            "refrigerated": True,
        },
        {
            "container_id": "C007",
            "size": 20,
            "weight": 13000,
            "destination": "Colombo",
            "priority": 3,
            "hazardous": False,
            "refrigerated": False,
        },
        {
            "container_id": "C008",
            "size": 40,
            "weight": 20000,
            "destination": "Mumbai",
            "priority": 1,
            "hazardous": False,
            "refrigerated": False,
        },
    ]

    return pd.DataFrame(containers)


def generate_slots():
    """
    Generate sample ship slots for our simplified vessel model.
    """

    slots = [
        {
            "slot_id": "B01-R01-T01",
            "bay": 1,
            "row": 1,
            "tier": 1,
            "size": 20,
            "max_weight": 30000,
            "refrigerated": False,
            "hazardous_allowed": True,
        },
        {
            "slot_id": "B01-R02-T01",
            "bay": 1,
            "row": 2,
            "tier": 1,
            "size": 40,
            "max_weight": 35000,
            "refrigerated": False,
            "hazardous_allowed": True,
        },
        {
            "slot_id": "B01-R03-T01",
            "bay": 1,
            "row": 3,
            "tier": 1,
            "size": 20,
            "max_weight": 30000,
            "refrigerated": True,
            "hazardous_allowed": False,
        },
        {
            "slot_id": "B02-R01-T01",
            "bay": 2,
            "row": 1,
            "tier": 1,
            "size": 40,
            "max_weight": 35000,
            "refrigerated": False,
            "hazardous_allowed": True,
        },
        {
            "slot_id": "B02-R02-T01",
            "bay": 2,
            "row": 2,
            "tier": 1,
            "size": 20,
            "max_weight": 30000,
            "refrigerated": True,
            "hazardous_allowed": False,
        },
        {
            "slot_id": "B02-R03-T01",
            "bay": 2,
            "row": 3,
            "tier": 1,
            "size": 40,
            "max_weight": 35000,
            "refrigerated": False,
            "hazardous_allowed": True,
        },
        {
            "slot_id": "B03-R01-T01",
            "bay": 3,
            "row": 1,
            "tier": 1,
            "size": 20,
            "max_weight": 30000,
            "refrigerated": False,
            "hazardous_allowed": True,
        },
        {
            "slot_id": "B03-R02-T01",
            "bay": 3,
            "row": 2,
            "tier": 1,
            "size": 40,
            "max_weight": 35000,
            "refrigerated": True,
            "hazardous_allowed": False,
        },
    ]

    return pd.DataFrame(slots)


if __name__ == "__main__":

    containers = generate_containers()
    slots = generate_slots()

    containers.to_csv(
        "datasets/generated/containers.csv",
        index=False
    )

    slots.to_csv(
        "datasets/generated/slots.csv",
        index=False
    )

    print("\n===== CONTAINER DATA =====")
    print(containers.to_string(index=False))

    print("\n===== SHIP SLOT DATA =====")
    print(slots.to_string(index=False))

    print("\nCSV files created successfully.")