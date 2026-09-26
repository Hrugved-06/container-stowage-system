import pandas as pd

try:
    from .algorithms import greedy
    from .evaluation import evaluate_solution
except ImportError:
    from algorithms import greedy
    from evaluation import evaluate_solution


containers = pd.read_csv(
    "datasets/generated/containers.csv"
)

slots = pd.read_csv(
    "datasets/generated/slots.csv"
)


solution = greedy(
    containers,
    slots
)


metrics = evaluate_solution(
    solution,
    containers,
    slots
)


print("\n===== EVALUATION TEST =====\n")

print("Assignment Rate:", metrics["assignment_rate"])
print("Slot Utilization:", metrics["slot_utilization"])
print("Total Loaded Weight:", metrics["total_loaded_weight"])
print("Average Container Weight:", metrics["average_container_weight"])
print("Total TEU:", metrics["total_teu"])
print("Constraint Violations:", metrics["constraint_violations"])


assert metrics["assignment_rate"] >= 0
assert metrics["slot_utilization"] >= 0
assert metrics["total_loaded_weight"] >= 0
assert metrics["average_container_weight"] >= 0
assert metrics["total_teu"] >= 0
assert metrics["constraint_violations"] == 0


print("\nEvaluation test PASSED.")