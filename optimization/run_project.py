import os
import shutil

from .run_experiments import run


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

DATASET_ROOT = os.path.join(
    PROJECT_ROOT,
    "datasets"
)

GENERATED_ROOT = os.path.join(
    DATASET_ROOT,
    "generated"
)

CUSTOM_ROOT = os.path.join(
    DATASET_ROOT,
    "custom"
)

ACTIVE_CONTAINER_FILE = os.path.join(
    GENERATED_ROOT,
    "containers.csv"
)

ACTIVE_SLOT_FILE = os.path.join(
    GENERATED_ROOT,
    "slots.csv"
)


DATASETS = {
    "1": {
        "name": "Demo",
        "description": "8 containers / 8 slots",
        "containers": os.path.join(
            GENERATED_ROOT,
            "containers.csv"
        ),
        "slots": os.path.join(
            GENERATED_ROOT,
            "slots.csv"
        )
    },

    "2": {
        "name": "Small",
        "description": "50 containers / 80 slots",
        "containers": os.path.join(
            GENERATED_ROOT,
            "small",
            "containers.csv"
        ),
        "slots": os.path.join(
            GENERATED_ROOT,
            "small",
            "slots.csv"
        )
    },

    "3": {
        "name": "Medium",
        "description": "100 containers / 160 slots",
        "containers": os.path.join(
            GENERATED_ROOT,
            "medium",
            "containers.csv"
        ),
        "slots": os.path.join(
            GENERATED_ROOT,
            "medium",
            "slots.csv"
        )
    },

    "4": {
        "name": "Large",
        "description": "250 containers / 400 slots",
        "containers": os.path.join(
            GENERATED_ROOT,
            "large",
            "containers.csv"
        ),
        "slots": os.path.join(
            GENERATED_ROOT,
            "large",
            "slots.csv"
        )
    },

    "5": {
        "name": "Custom",
        "description": "Use datasets/custom/containers.csv and slots.csv",
        "containers": os.path.join(
            CUSTOM_ROOT,
            "containers.csv"
        ),
        "slots": os.path.join(
            CUSTOM_ROOT,
            "slots.csv"
        )
    }
}


def validate_dataset(dataset):

    container_file = dataset["containers"]
    slot_file = dataset["slots"]

    if not os.path.exists(container_file):
        raise FileNotFoundError(
            f"Container file not found:\n{container_file}"
        )

    if not os.path.exists(slot_file):
        raise FileNotFoundError(
            f"Slot file not found:\n{slot_file}"
        )


def activate_dataset(dataset):

    validate_dataset(dataset)

    shutil.copy2(
        dataset["containers"],
        ACTIVE_CONTAINER_FILE
    )

    shutil.copy2(
        dataset["slots"],
        ACTIVE_SLOT_FILE
    )

    print()
    print("Dataset activated successfully.")
    print(
        f"Containers: {dataset['containers']}"
    )
    print(
        f"Slots:      {dataset['slots']}"
    )
    print()


def show_menu():

    print()
    print("========================================")
    print("CONTAINER STOWAGE EXPERIMENT RUNNER")
    print("========================================")
    print()

    for key, dataset in DATASETS.items():

        print(
            f"{key}. {dataset['name']:<8} "
            f"- {dataset['description']}"
        )

    print()
    print("0. Exit")
    print()


def main():

    while True:

        show_menu()

        choice = input(
            "Select dataset: "
        ).strip()

        if choice == "0":
            print()
            print("Exiting.")
            return

        if choice not in DATASETS:

            print()
            print("Invalid selection.")
            continue

        dataset = DATASETS[choice]

        try:

            print()
            print(
                f"Selected: {dataset['name']}"
            )

            activate_dataset(dataset)

            if dataset["name"] == "Custom":

                print(
                    "Custom dataset uses:"
                )
                print(
                    "  datasets/custom/containers.csv"
                )
                print(
                    "  datasets/custom/slots.csv"
                )

            print()
            print(
                "Starting optimization experiments..."
            )
            print()

            run()

            print()
            print(
                "Experiment completed successfully."
            )

        except Exception as error:

            print()
            print("ERROR")
            print("----------------------------------------")
            print(error)
            print("----------------------------------------")

        print()

        again = input(
            "Run another dataset? (y/n): "
        ).strip().lower()

        if again != "y":
            print()
            print("Finished.")
            break


if __name__ == "__main__":
    main()