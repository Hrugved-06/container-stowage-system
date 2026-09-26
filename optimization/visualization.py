import os
import pandas as pd
import matplotlib.pyplot as plt


RESULT_DIR = "experiments/results"
GRAPH_DIR = "experiments/graphs"

os.makedirs(
    GRAPH_DIR,
    exist_ok=True
)


def create_graphs():

    comparison_file = os.path.join(
        RESULT_DIR,
        "algorithm_comparison.csv"
    )

    if not os.path.exists(
        comparison_file
    ):

        print(
            "Comparison CSV not found."
        )

        return

    df = pd.read_csv(
        comparison_file
    )

    if df.empty:

        print(
            "No results available."
        )

        return


    # -------------------------------------------------
    # Assignment Rate
    # -------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        df["algorithm"],
        df["assignment_rate"]
    )

    plt.ylabel(
        "Assignment Rate (%)"
    )

    plt.xlabel(
        "Algorithm"
    )

    plt.title(
        "Algorithm vs Assignment Rate"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            GRAPH_DIR,
            "algorithm_vs_assignment_rate.png"
        ),
        dpi=200
    )

    plt.close()


    # -------------------------------------------------
    # Runtime
    # -------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        df["algorithm"],
        df["runtime_seconds"]
    )

    plt.ylabel(
        "Runtime (seconds)"
    )

    plt.xlabel(
        "Algorithm"
    )

    plt.title(
        "Algorithm vs Runtime"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            GRAPH_DIR,
            "algorithm_vs_runtime.png"
        ),
        dpi=200
    )

    plt.close()


    # -------------------------------------------------
    # Weight Imbalance
    # -------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        df["algorithm"],
        df["weight_imbalance_std"]
    )

    plt.ylabel(
        "Weight Imbalance"
    )

    plt.xlabel(
        "Algorithm"
    )

    plt.title(
        "Algorithm vs Weight Imbalance"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            GRAPH_DIR,
            "algorithm_vs_imbalance.png"
        ),
        dpi=200
    )

    plt.close()


    # -------------------------------------------------
    # Objective
    # -------------------------------------------------

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        df["algorithm"],
        df["objective_score"]
    )

    plt.ylabel(
        "Objective Score"
    )

    plt.xlabel(
        "Algorithm"
    )

    plt.title(
        "Algorithm vs Objective Score"
    )

    plt.xticks(
        rotation=25,
        ha="right"
    )

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            GRAPH_DIR,
            "algorithm_vs_objective.png"
        ),
        dpi=200
    )

    plt.close()


    print(
        "Research graphs generated successfully."
    )


if __name__ == "__main__":

    create_graphs()