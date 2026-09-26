import pandas as pd


containers = pd.read_csv("datasets/generated/containers.csv")
slots = pd.read_csv("datasets/generated/slots.csv")

print("\nNumber of containers:", len(containers))
print("Number of slots:", len(slots))

print("\nContainer columns:")
print(list(containers.columns))

print("\nSlot columns:")
print(list(slots.columns))