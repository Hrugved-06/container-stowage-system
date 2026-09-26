"""Generate deterministic, operationally realistic synthetic benchmark datasets.

These datasets are not claimed to be proprietary shipping-line manifests. They
model a multi-port service from JNPT (Mumbai) through Colombo and Port Klang to
Singapore, with mixed 20/40-ft cargo, reefer/hazardous constraints, priorities,
and demand pressure that makes the optimizer choose between competing cargo.
"""
from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parent / "generated"
DESTINATIONS = [
    ("Colombo", 1, 0.36),
    ("Port Klang", 2, 0.34),
    ("Singapore", 3, 0.30),
]

SCENARIOS = {
    "demo": {"slots": 12, "containers": 12, "bays": 2, "rows": 3, "tiers": 2, "seed": 11},
    "small": {"slots": 80, "containers": 84, "bays": 8, "rows": 5, "tiers": 2, "seed": 21},
    "medium": {"slots": 160, "containers": 176, "bays": 10, "rows": 8, "tiers": 2, "seed": 31},
    "large": {"slots": 400, "containers": 460, "bays": 20, "rows": 10, "tiers": 2, "seed": 41},
}


def weighted_choice(rng, pairs):
    values = [p[0] for p in pairs]
    weights = [p[1] for p in pairs]
    return rng.choices(values, weights=weights, k=1)[0]


def make_slots(cfg):
    rng = random.Random(cfg["seed"])
    rows = []
    stack_index = 0
    for bay in range(1, cfg["bays"] + 1):
        for row in range(1, cfg["rows"] + 1):
            stack_index += 1
            # Keep both tiers in one stack the same physical size.
            size = 20 if ((bay * 7 + row * 3 + cfg["seed"]) % 10) < 6 else 40
            reefer_stack = ((bay + row + cfg["seed"]) % 5 == 0)
            hazardous_stack = ((bay * 2 + row + cfg["seed"]) % 3 == 0)
            for tier in range(1, cfg["tiers"] + 1):
                rows.append({
                    "slot_id": f"B{bay:02d}-R{row:02d}-T{tier:02d}",
                    "bay": bay,
                    "row": row,
                    "tier": tier,
                    "size": size,
                    "max_weight": 30480,
                    "reefer_capable": bool(reefer_stack or rng.random() < 0.06),
                    "hazardous_allowed": bool(hazardous_stack or rng.random() < 0.10),
                })
    assert len(rows) == cfg["slots"]
    return pd.DataFrame(rows)


def make_containers(cfg, slots):
    rng = random.Random(cfg["seed"] + 1000)
    slot_20_share = float((slots["size"] == 20).mean())
    rows = []
    for i in range(1, cfg["containers"] + 1):
        size = 20 if rng.random() < slot_20_share else 40
        # Realistic operational spread: heavier cargo exists, but stays below
        # the simplified 30,480 kg slot limit used by the prototype.
        if size == 20:
            weight = int(rng.triangular(5500, 29200, 16500))
        else:
            weight = int(rng.triangular(8500, 30000, 20500))

        dest = rng.choices(
            [d[0] for d in DESTINATIONS],
            weights=[d[2] for d in DESTINATIONS],
            k=1,
        )[0]
        dest_order = next(d[1] for d in DESTINATIONS if d[0] == dest)
        priority = weighted_choice(rng, [(1, 0.24), (2, 0.51), (3, 0.25)])
        refrigerated = rng.random() < 0.12
        hazardous = rng.random() < 0.075
        # Keep the rare combined reefer+hazardous case but don't overproduce it.
        if refrigerated and hazardous and rng.random() < 0.70:
            hazardous = False

        rows.append({
            "container_id": f"C{i:05d}",
            "size": size,
            "weight": weight,
            "destination": dest,
            "destination_order": dest_order,
            "priority": priority,
            "hazardous": bool(hazardous),
            "refrigerated": bool(refrigerated),
        })
    return pd.DataFrame(rows)


def main():
    for name, cfg in SCENARIOS.items():
        folder = ROOT / name
        folder.mkdir(parents=True, exist_ok=True)
        slots = make_slots(cfg)
        containers = make_containers(cfg, slots)
        containers.to_csv(folder / "containers.csv", index=False)
        slots.to_csv(folder / "slots.csv", index=False)
        print(name, len(containers), len(slots), round(len(containers) / len(slots), 3))


if __name__ == "__main__":
    main()
