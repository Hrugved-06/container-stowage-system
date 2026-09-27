"""Reproducible RCSPPSuite -> project benchmark adapter.

This adapter intentionally creates *reduced, single-stage* benchmark datasets from
public RCSPPSuite instances. It preserves cargo attributes that the academic
prototype models (container type/size, weight, POL/POD, reefer, IMDG flag,
pseudoprofit) and vessel-position attributes available from the vessel profile
(bay, row, tier, stack capacity and reefer positions).

It does NOT claim full RCSPP compliance. Advanced RCSPP constraints such as
hydrostatics, GM, ballast, bending moment, lashing, crane limits, block stowage,
IMDG pairwise segregation, and dynamic arrival-condition evolution are retained
in the source XML files but are outside the current optimizer's mathematical
model. The generated manifest records this explicitly for reproducibility.
"""
from __future__ import annotations

import json
import math
import random
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RCSPP_ROOT = ROOT / "datasets" / "rcspp"
SOURCE = RCSPP_ROOT / "source"
GENERATED = RCSPP_ROOT / "generated"

PROFILES = {
    "rcspp_small": {
        "instance": "s_01",
        "vessel": "vessel_s",
        "containers": 84,
        "slots": 80,
        "seed": 4201,
        "preferred_pol": 4,
        "label": "RCSPPSuite Small (adapted s_01)",
    },
    "rcspp_medium": {
        "instance": "m_01",
        "vessel": "vessel_m",
        "containers": 176,
        "slots": 160,
        "seed": 4202,
        "preferred_pol": 2,
        "label": "RCSPPSuite Medium (adapted m_01)",
    },
    "rcspp_large": {
        "instance": "l_01",
        "vessel": "vessel_l",
        "containers": 460,
        "slots": 400,
        "seed": 4203,
        "preferred_pol": 1,
        "label": "RCSPPSuite Large (adapted l_01)",
    },
}


def _text(node, tag, default=None):
    child = node.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def read_instance(instance_name: str):
    path = SOURCE / "Instances" / f"{instance_name}.xml"
    root = ET.parse(path).getroot()

    voyage = []
    for port in root.find("Voyage").findall("Port"):
        voyage.append({
            "code": int(port.attrib.get("Code", 0)),
            "max_lc": int(float(port.attrib.get("MaxLC", 0))),
        })

    cargo = []
    for container in root.find("LoadList").findall("Container"):
        cargo.append({
            "source_container_id": int(_text(container, "ID", 0)),
            "container_type": _text(container, "Type", "20DC"),
            "weight_t": float(_text(container, "Weight", 0.0)),
            "pol": int(float(_text(container, "POL", 0))),
            "pod": int(float(_text(container, "POD", 0))),
            "reefer": bool(int(float(_text(container, "Reefer", 0)))),
            "imdg": bool(int(float(_text(container, "Imdg", 0)))),
            "imdg_type": int(float(_text(container, "ImdgType", 0) or 0)),
            "points": int(float(_text(container, "Points", 0) or 0)),
        })

    return path, pd.DataFrame(cargo), voyage


def read_vessel(vessel_name: str):
    path = SOURCE / "Vessels" / f"{vessel_name}.xml"
    root = ET.parse(path).getroot()
    cells = []

    for bay in root.find("Bays").findall("Bay"):
        bay_id = int(bay.attrib["Name"])
        stacks = bay.find("Stacks")
        if stacks is None:
            continue
        for stack in stacks.findall("Stack"):
            a = stack.attrib
            start = int(a["StartTier"])
            end = int(a["EndTier"])
            tiers = list(range(start, end + 1, 2))
            if not tiers:
                continue

            reefers = set()
            raw = a.get("ReeferPositions", "")
            if raw:
                for token in raw.replace(",", ";").split(";"):
                    token = token.strip()
                    if token:
                        reefers.add(int(token))

            stack_max_t = float(a["MaxWeight"])
            conservative_cell_limit_t = stack_max_t / len(tiers)

            for tier in tiers:
                cells.append({
                    "bay": bay_id,
                    "row": int(a["Row"]),
                    "tier": tier,
                    "source_stack_index": int(a["Index"]),
                    "level": a.get("Level", ""),
                    "reefer_capable": tier in reefers,
                    "stack_max_weight_t": stack_max_t,
                    "max_weight": round(conservative_cell_limit_t * 1000.0, 3),
                })

    return path, pd.DataFrame(cells)


def _choose_pol(cargo: pd.DataFrame, required: int) -> int:
    """Choose a load port with enough cargo and strong POD diversity.

    Destination diversity is important because the reduced benchmark is also
    intended to exercise destination mixing and rehandling metrics.
    """
    stats = (
        cargo.groupby("pol")
        .agg(count=("source_container_id", "size"), pod_diversity=("pod", "nunique"))
        .reset_index()
    )
    eligible = stats[stats["count"] >= required].copy()
    if eligible.empty:
        eligible = stats.copy()
    eligible = eligible.sort_values(
        ["pod_diversity", "count", "pol"],
        ascending=[False, False, True],
    )
    return int(eligible.iloc[0]["pol"])


def _sample_cargo(cargo: pd.DataFrame, n: int, seed: int, voyage_codes: list[int], preferred_pol=None):
    if preferred_pol is not None and len(cargo[cargo["pol"] == int(preferred_pol)]) >= n:
        pol = int(preferred_pol)
    else:
        pol = _choose_pol(cargo, n)
    candidates = cargo[cargo["pol"] == pol].copy()
    if len(candidates) < n:
        candidates = cargo.copy()

    # Preserve rare special-cargo rows when the reduced sample is smaller than
    # the source group. This keeps reefer/IMDG compatibility meaningful instead
    # of accidentally sampling every rare record away.
    forced = candidates[candidates["imdg"]].copy()
    forced = forced.head(min(len(forced), max(1, min(5, n // 10))))
    remaining = candidates.drop(index=forced.index)
    need = min(n, len(candidates)) - len(forced)
    sampled_rest = remaining.sample(n=need, random_state=seed) if need > 0 else remaining.head(0)
    sampled = pd.concat([forced, sampled_rest], ignore_index=False).sample(frac=1, random_state=seed + 1).copy()

    voyage_order = {code: idx for idx, code in enumerate(voyage_codes)}
    sampled["size"] = sampled["container_type"].map(lambda x: 20 if str(x).startswith("20") else 40)
    sampled["weight"] = (sampled["weight_t"] * 1000.0).round(3)
    sampled["destination"] = sampled["pod"].map(lambda x: f"Port {int(x)}")
    sampled["destination_order"] = sampled["pod"].map(lambda x: voyage_order.get(int(x), 999))
    sampled["priority"] = sampled["points"].map(lambda x: 1 if float(x) >= 100 else (2 if float(x) >= 50 else 3))
    sampled["hazardous"] = sampled["imdg"].astype(bool)
    sampled["refrigerated"] = sampled["reefer"].astype(bool)
    sampled["container_id"] = sampled["source_container_id"].map(lambda x: f"RC-{int(x):06d}")

    columns = [
        "container_id", "size", "weight", "destination", "destination_order",
        "priority", "hazardous", "refrigerated", "source_container_id",
        "container_type", "pol", "pod", "points", "imdg_type", "weight_t",
    ]
    return sampled[columns].reset_index(drop=True), pol


def _assign_slot_sizes(cells: pd.DataFrame, cargo: pd.DataFrame, target_slots: int, seed: int):
    """Select compact multi-tier stacks and map RCSPP cells to project slots.

    Selecting positions stack-by-stack (rather than isolated random cells) makes
    destination order and rehandling metrics meaningful in the reduced model.
    """
    rng = random.Random(seed)
    target_slots = min(target_slots, len(cells))

    work = cells.copy()
    grouped = []
    for stack_index, stack in work.groupby("source_stack_index", sort=True):
        stack = stack.sort_values("tier").copy()
        grouped.append({
            "stack_index": int(stack_index),
            "rows": stack,
            "count": len(stack),
            "reefer_count": int(stack["reefer_capable"].sum()),
            "max_cell_weight": float(stack["max_weight"].max()),
        })

    # We need enough reefer-capable positions for the sampled reefer cargo, but
    # otherwise keep stack selection deterministic and varied.
    desired_reefer = int(cargo["refrigerated"].sum())
    reefer_groups = [g for g in grouped if g["reefer_count"] > 0]
    normal_groups = [g for g in grouped if g["reefer_count"] == 0]
    rng.shuffle(reefer_groups)
    rng.shuffle(normal_groups)

    chosen_groups = []
    selected_count = 0
    selected_reefers = 0

    # First add enough stacks that contain reefer positions.
    for g in reefer_groups:
        if selected_count >= target_slots or selected_reefers >= desired_reefer:
            break
        chosen_groups.append(g)
        selected_count += g["count"]
        selected_reefers += g["reefer_count"]

    remaining_groups = [g for g in grouped if g not in chosen_groups]
    rng.shuffle(remaining_groups)
    for g in remaining_groups:
        if selected_count >= target_slots:
            break
        chosen_groups.append(g)
        selected_count += g["count"]
        selected_reefers += g["reefer_count"]

    selected_parts = []
    remaining = target_slots
    for g in chosen_groups:
        if remaining <= 0:
            break
        stack = g["rows"].sort_values("tier")
        take = min(remaining, len(stack))
        # If a stack is only partially used, retain lower tiers first so the
        # reduced benchmark never creates artificial floating positions.
        selected_parts.append(stack.head(take))
        remaining -= take

    selected = pd.concat(selected_parts, ignore_index=True)

    # Assign one nominal project size to each selected stack. The RCSPP source
    # supports two 20-foot halves or one 40-foot container per physical cell;
    # this academic model uses one container per adapted position, so the stack
    # size mix is matched to the sampled cargo distribution and recorded in the
    # manifest as a model reduction.
    p20 = float((cargo["size"] == 20).mean()) if len(cargo) else 0.5
    stack_ids = selected["source_stack_index"].drop_duplicates().tolist()
    n20_stacks = int(round(len(stack_ids) * p20))
    size_labels = [20] * n20_stacks + [40] * (len(stack_ids) - n20_stacks)
    rng.shuffle(size_labels)
    stack_size = dict(zip(stack_ids, size_labels))
    selected["size"] = selected["source_stack_index"].map(stack_size).astype(int)

    selected["hazardous_allowed"] = True  # RCSPP IMDG separation is pairwise, not a slot permission.
    selected = selected.sort_values(["bay", "row", "tier"]).reset_index(drop=True)
    selected["slot_id"] = selected.apply(
        lambda r: f"RCSPP-B{int(r['bay']):02d}-R{int(r['row']):02d}-T{int(r['tier']):02d}-{int(r.name)+1:04d}", axis=1
    )

    columns = [
        "slot_id", "bay", "row", "tier", "size", "max_weight",
        "reefer_capable", "hazardous_allowed", "source_stack_index",
        "level", "stack_max_weight_t",
    ]
    return selected[columns]


def generate_profile(dataset_id: str, cfg: dict):
    inst_path, cargo_raw, voyage = read_instance(cfg["instance"])
    vessel_path, cells = read_vessel(cfg["vessel"])
    voyage_codes = [p["code"] for p in voyage]

    cargo, selected_pol = _sample_cargo(
        cargo_raw, cfg["containers"], cfg["seed"], voyage_codes, cfg.get("preferred_pol")
    )
    slots = _assign_slot_sizes(cells, cargo, cfg["slots"], cfg["seed"])

    out = GENERATED / dataset_id
    out.mkdir(parents=True, exist_ok=True)
    cargo.to_csv(out / "containers.csv", index=False)
    slots.to_csv(out / "slots.csv", index=False)

    manifest = {
        "dataset_id": dataset_id,
        "display_name": cfg["label"],
        "benchmark_suite": "RCSPPSuite",
        "source_instance": cfg["instance"],
        "source_vessel": cfg["vessel"],
        "source_instance_file": str(inst_path.relative_to(ROOT)),
        "source_vessel_file": str(vessel_path.relative_to(ROOT)),
        "source_loadlist_count": int(len(cargo_raw)),
        "source_physical_cell_count": int(len(cells)),
        "selected_pol": int(selected_pol),
        "voyage_port_codes": voyage_codes,
        "generated_container_count": int(len(cargo)),
        "generated_slot_count": int(len(slots)),
        "random_seed": int(cfg["seed"]),
        "adaptation": {
            "mode": "reduced single-stage RCSPPSuite-derived benchmark",
            "preserved": [
                "source container identity", "20/40-foot type", "weight", "POL", "POD",
                "voyage destination order", "reefer flag", "IMDG flag/type", "pseudoprofit/priority",
                "vessel bay-row-tier geometry", "reefer positions", "stack maximum-weight data",
            ],
            "transformations": [
                "Container weights are converted from tonnes to kilograms for compatibility with the existing optimizer.",
                "RCSPP stack maximum weight is conservatively divided across stack tiers to obtain per-position max_weight.",
                "Physical cells are deterministically assigned a 20/40-foot slot type to match the sampled cargo mix because the academic optimizer uses a one-container-per-slot representation.",
                "RCSPP Points are mapped to priority (>=100 -> 1, >=50 -> 2, otherwise 3).",
            ],
            "not_modeled": [
                "dynamic arrival-condition evolution across ports", "ballast optimization", "hydrostatic GM",
                "trim and displacement interpolation", "bending moment", "lashing force limits",
                "crane makespan/long-crane constraints", "paired block stowage", "40-foot two-half occupancy",
                "pairwise IMDG segregation distance rules",
            ],
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def generate_all():
    GENERATED.mkdir(parents=True, exist_ok=True)
    manifests = []
    for dataset_id, cfg in PROFILES.items():
        manifests.append(generate_profile(dataset_id, cfg))
    (GENERATED / "manifest_index.json").write_text(json.dumps(manifests, indent=2), encoding="utf-8")
    return manifests


if __name__ == "__main__":
    for item in generate_all():
        print(
            f"{item['dataset_id']}: {item['generated_container_count']} containers / "
            f"{item['generated_slot_count']} slots from {item['source_instance']}"
        )
