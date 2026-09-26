import os
import random

import pandas as pd


DESTINATIONS = [
    ("Mumbai", 1),
    ("Dubai", 2),
    ("Singapore", 3),
    ("Colombo", 4)
]


def generate_containers(
    number,
    seed=42
):

    rng = random.Random(
        seed
    )

    rows = []

    for i in range(1, number + 1):

        size = rng.choice(
            [20, 40]
        )

        weight_limit = (
            30000
            if size == 20
            else 35000
        )

        weight = rng.randint(
            8000,
            weight_limit
        )

        destination, order = (
            rng.choice(
                DESTINATIONS
            )
        )

        priority = rng.choice(
            [1, 2, 3]
        )

        hazardous = (
            rng.random() < 0.08
        )

        refrigerated = (
            rng.random() < 0.12
        )

        rows.append(
            {
                "container_id":
                    f"C{i:05d}",

                "size":
                    size,

                "weight":
                    weight,

                "destination":
                    destination,

                "destination_order":
                    order,

                "priority":
                    priority,

                "hazardous":
                    hazardous,

                "refrigerated":
                    refrigerated
            }
        )

    return pd.DataFrame(
        rows
    )


def generate_slots(
    number,
    seed=42
):

    rng = random.Random(
        seed
    )

    rows = []

    for i in range(
        number
    ):

        bay = (
            i // 10
        ) + 1

        position = (
            i % 10
        )

        row = (
            position // 2
        ) + 1

        tier = (
            position % 2
        ) + 1

        size = rng.choice(
            [20, 40]
        )

        max_weight = (
            30000
            if size == 20
            else 35000
        )

        reefer = (
            rng.random() < 0.20
        )

        hazardous = (
            rng.random() < 0.85
        )

        rows.append(
            {
                "slot_id":
                    f"B{bay:02d}-R{row:02d}-T{tier:02d}",

                "bay":
                    bay,

                "row":
                    row,

                "tier":
                    tier,

                "size":
                    size,

                "max_weight":
                    max_weight,

                "reefer_capable":
                    reefer,

                "hazardous_allowed":
                    hazardous
            }
        )

    return pd.DataFrame(
        rows
    )


def generate_benchmark(
    name,
    containers,
    slots,
    seed=42
):

    path = (
        f"datasets/generated/{name}"
    )

    os.makedirs(
        path,
        exist_ok=True
    )

    container_data = (
        generate_containers(
            containers,
            seed
        )
    )

    slot_data = (
        generate_slots(
            slots,
            seed
        )
    )

    container_data.to_csv(
        f"{path}/containers.csv",
        index=False
    )

    slot_data.to_csv(
        f"{path}/slots.csv",
        index=False
    )

    print(
        f"Generated {name}: "
        f"{containers} containers, "
        f"{slots} slots"
    )


if __name__ == "__main__":

    generate_benchmark(
        "small",
        50,
        80
    )

    generate_benchmark(
        "medium",
        100,
        160
    )

    generate_benchmark(
        "large",
        250,
        400
    )

    print(
        "\nBenchmark generation complete."
    )