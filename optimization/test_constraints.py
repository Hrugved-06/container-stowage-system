import pandas as pd

try:
    from .constraints import check_all_constraints
except ImportError:
    from constraints import check_all_constraints


containers = pd.read_csv(
    "datasets/generated/containers.csv"
)

slots = pd.read_csv(
    "datasets/generated/slots.csv"
)


print("\n===== TESTING ALL CONTAINER-SLOT COMBINATIONS =====\n")


valid_count = 0
invalid_count = 0


for _, container in containers.iterrows():

    for _, slot in slots.iterrows():

        results = check_all_constraints(
            container,
            slot
        )

        if results["valid"]:
            valid_count += 1
        else:
            invalid_count += 1


print("Total containers:", len(containers))
print("Total slots:", len(slots))

print(
    "Total possible combinations:",
    len(containers) * len(slots)
)

print("Valid combinations:", valid_count)
print("Invalid combinations:", invalid_count)