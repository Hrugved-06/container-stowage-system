import os
import pandas as pd
import matplotlib.pyplot as plt


RESULTS_FILE = "experiments/results/algorithm_comparison.csv"
OUTPUT_DIR = "experiments/results/pareto"


def is_dominated(row, other):
    """
    Returns True if 'row' is dominated by 'other'.

    Objectives:
    - minimize runtime
    - minimize objective score
    - maximize assignment rate
    - minimize weight imbalance
    - minimize rehandling
    """

    row_runtime = float(row["runtime_seconds"])
    other_runtime = float(other["runtime_seconds"])

    row_objective = float(row["objective_score"])
    other_objective = float(other["objective_score"])

    row_assignment = float(row["assignment_rate"])
    other_assignment = float(other["assignment_rate"])

    row_imbalance = float(row["weight_imbalance_std"])
    other_imbalance = float(other["weight_imbalance_std"])

    row_rehandling = float(row["rehandling"])
    other_rehandling = float(other["rehandling"])

    no_worse = (
        other_runtime <= row_runtime
        and other_objective <= row_objective
        and other_assignment >= row_assignment
        and other_imbalance <= row_imbalance
        and other_rehandling <= row_rehandling
    )

    strictly_better = (
        other_runtime < row_runtime
        or other_objective < row_objective
        or other_assignment > row_assignment
        or other_imbalance < row_imbalance
        or other_rehandling < row_rehandling
    )

    return no_worse and strictly_better


def calculate_pareto_front(df):
    """
    Calculate the non-dominated solutions.
    """

    pareto_rows = []

    for index, row in df.iterrows():

        dominated = False

        for other_index, other in df.iterrows():

            if index == other_index:
                continue

            if is_dominated(row, other):
                dominated = True
                break

        if not dominated:
            pareto_rows.append(row)

    if not pareto_rows:
        return pd.DataFrame(columns=df.columns)

    return pd.DataFrame(pareto_rows).reset_index(drop=True)


def create_runtime_objective_plot(df, pareto_df, output_file):
    """
    Create Runtime vs Objective Score Pareto plot.
    """

    plt.figure(figsize=(10, 6))

    plt.scatter(
        df["runtime_seconds"],
        df["objective_score"],
        s=80,
        label="Algorithms"
    )

    if not pareto_df.empty:

        plt.scatter(
            pareto_df["runtime_seconds"],
            pareto_df["objective_score"],
            s=120,
            marker="D",
            label="Pareto Front"
        )

        for _, row in pareto_df.iterrows():

            plt.annotate(
                row["algorithm"],
                (
                    row["runtime_seconds"],
                    row["objective_score"]
                ),
                xytext=(6, 6),
                textcoords="offset points"
            )

    plt.xlabel("Runtime (seconds)")
    plt.ylabel("Objective Score")
    plt.title("Pareto Analysis: Runtime vs Objective Score")

    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(output_file, dpi=300)
    plt.close()


def create_runtime_assignment_plot(df, output_file):
    """
    Create Runtime vs Assignment Rate plot.
    """

    plt.figure(figsize=(10, 6))

    plt.scatter(
        df["runtime_seconds"],
        df["assignment_rate"],
        s=100
    )

    for _, row in df.iterrows():

        plt.annotate(
            row["algorithm"],
            (
                row["runtime_seconds"],
                row["assignment_rate"]
            ),
            xytext=(6, 6),
            textcoords="offset points"
        )

    plt.xlabel("Runtime (seconds)")
    plt.ylabel("Assignment Rate (%)")
    plt.title("Algorithm Runtime vs Assignment Rate")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_file, dpi=300)
    plt.close()


def run_pareto():

    print()
    print("========================================")
    print("PARETO ANALYSIS")
    print("========================================")
    print()

    if not os.path.exists(RESULTS_FILE):

        raise FileNotFoundError(
            f"Results file not found: {RESULTS_FILE}"
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(RESULTS_FILE)

    print(f"Loaded {len(df)} algorithm results.")
    print()

    required_columns = [
        "algorithm",
        "runtime_seconds",
        "assignment_rate",
        "objective_score",
        "weight_imbalance_std",
        "rehandling"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:

        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    # Current experiment runner records only
    # successfully completed algorithms.
    # Therefore we do not use a 'status' column.

    df = df.dropna(
        subset=required_columns
    ).copy()

    print("Algorithms included:")
    print(
        df["algorithm"].to_string(index=False)
    )
    print()

    pareto_df = calculate_pareto_front(df)

    pareto_file = os.path.join(
        OUTPUT_DIR,
        "pareto_front.csv"
    )

    pareto_df.to_csv(
        pareto_file,
        index=False
    )

    all_results_file = os.path.join(
        OUTPUT_DIR,
        "pareto_analysis_all.csv"
    )

    df.to_csv(
        all_results_file,
        index=False
    )

    runtime_objective_plot = os.path.join(
        OUTPUT_DIR,
        "pareto_runtime_vs_objective.png"
    )

    create_runtime_objective_plot(
        df,
        pareto_df,
        runtime_objective_plot
    )

    runtime_assignment_plot = os.path.join(
        OUTPUT_DIR,
        "runtime_vs_assignment.png"
    )

    create_runtime_assignment_plot(
        df,
        runtime_assignment_plot
    )

    print("========================================")
    print("PARETO FRONT")
    print("========================================")
    print()

    if pareto_df.empty:

        print("No Pareto solutions found.")

    else:

        print(
            pareto_df[
                [
                    "algorithm",
                    "runtime_seconds",
                    "assignment_rate",
                    "objective_score",
                    "weight_imbalance_std",
                    "rehandling"
                ]
            ].to_string(index=False)
        )

    print()
    print("Files saved:")
    print(pareto_file)
    print(all_results_file)
    print(runtime_objective_plot)
    print(runtime_assignment_plot)
    print()

    print("Pareto analysis completed successfully.")


if __name__ == "__main__":
    run_pareto()