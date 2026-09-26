import pandas as pd


CONTAINER_COLUMNS = [
    "container_id",
    "size",
    "weight",
    "destination",
    "destination_order",
    "priority",
    "hazardous",
    "refrigerated",
]

SLOT_COLUMNS = [
    "slot_id",
    "bay",
    "row",
    "tier",
    "size",
    "max_weight",
    "reefer_capable",
    "hazardous_allowed",
]


def validate_containers(df: pd.DataFrame):
    errors = []

    missing = [
        column
        for column in CONTAINER_COLUMNS
        if column not in df.columns
    ]

    if missing:
        errors.append(
            f"Missing container columns: {', '.join(missing)}"
        )

    if errors:
        return errors

    if df["container_id"].duplicated().any():
        errors.append("Duplicate container_id values found.")

    if df["size"].isna().any():
        errors.append("Container size contains missing values.")

    if df["weight"].isna().any():
        errors.append("Container weight contains missing values.")

    if (df["weight"] < 0).any():
        errors.append("Container weight cannot be negative.")

    if not df["size"].isin([20, 40]).all():
        errors.append(
            "Container size must contain only 20 or 40."
        )

    return errors


def validate_slots(df: pd.DataFrame):
    errors = []

    missing = [
        column
        for column in SLOT_COLUMNS
        if column not in df.columns
    ]

    if missing:
        errors.append(
            f"Missing slot columns: {', '.join(missing)}"
        )

    if errors:
        return errors

    if df["slot_id"].duplicated().any():
        errors.append("Duplicate slot_id values found.")

    if df["max_weight"].isna().any():
        errors.append("Slot max_weight contains missing values.")

    if (df["max_weight"] < 0).any():
        errors.append("Slot max_weight cannot be negative.")

    if not df["size"].isin([20, 40]).all():
        errors.append(
            "Slot size must contain only 20 or 40."
        )

    return errors


def validate_dataset(
    containers: pd.DataFrame,
    slots: pd.DataFrame
):
    container_errors = validate_containers(containers)
    slot_errors = validate_slots(slots)

    return {
        "valid": (
            len(container_errors) == 0
            and len(slot_errors) == 0
        ),
        "container_errors": container_errors,
        "slot_errors": slot_errors,
        "container_count": len(containers),
        "slot_count": len(slots),
    }