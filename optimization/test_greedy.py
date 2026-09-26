import pandas as pd

from greedy import greedy_stowage


containers = pd.read_csv(
    "datasets/generated/containers.csv"
)

slots = pd.read_csv(
    "datasets/generated/slots.csv"
)


result = greedy_stowage(
    containers,
    slots
)


print("\n===== GREEDY ALGORITHM TEST =====\n")

print(result.to_string(index=False))


assigned = result["slot_id"].notna().sum()

unassigned = result["slot_id"].isna().sum()


print("\n===== RESULT =====")

print("Total containers:", len(containers))
print("Assigned:", assigned)
print("Unassigned:", unassigned)

print(
    "Assignment rate:",
    f"{(assigned / len(containers)) * 100:.2f}%"
)