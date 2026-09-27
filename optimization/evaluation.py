import pandas as pd

try:
    from .constraints import check_all_constraints
except ImportError:
    from constraints import check_all_constraints


def _assigned(solution):
    if solution is None or solution.empty or "slot_id" not in solution.columns:
        return pd.DataFrame()
    return solution[solution["slot_id"].notna()].copy()


def calculate_assignment_rate(solution, containers=None):
    """Assigned unique input containers / total eligible input containers."""
    assigned = _assigned(solution)
    if containers is not None:
        denominator = len(containers)
    else:
        denominator = len(solution) if solution is not None else 0
    if denominator == 0:
        return 0.0
    if assigned.empty:
        return 0.0
    if "container_id" in assigned.columns:
        numerator = assigned["container_id"].nunique()
    else:
        numerator = len(assigned)
    return min(100.0, numerator / denominator * 100.0)


def calculate_slot_utilization(solution, slots):
    """Unique occupied slot IDs / available unique slot IDs.

    Counting unique slot IDs makes the metric robust to accidental duplicate rows
    and prevents impossible utilization values above 100% from being reported.
    """
    if slots is None or len(slots) == 0:
        return 0.0
    assigned = _assigned(solution)
    if assigned.empty:
        return 0.0
    used = assigned["slot_id"].astype(str).nunique()
    available = slots["slot_id"].astype(str).nunique() if "slot_id" in slots.columns else len(slots)
    if available == 0:
        return 0.0
    return min(100.0, used / available * 100.0)


def calculate_total_loaded_weight(solution):
    assigned = _assigned(solution)
    if assigned.empty:
        return 0.0
    return float(assigned["container_weight"].sum())


def calculate_average_container_weight(solution):
    assigned = _assigned(solution)
    if assigned.empty:
        return 0.0
    return float(assigned["container_weight"].mean())


def calculate_teu(solution):
    assigned = _assigned(solution)
    if assigned.empty:
        return 0
    return int((assigned["container_size"] / 20).sum())


def verify_solution_constraints(solution, containers, slots):
    """Return placement and structural integrity violations for a solution."""
    violations = []
    assigned = _assigned(solution)
    if assigned.empty:
        return violations

    # A valid one-container-per-slot solution cannot repeat either resource.
    if "slot_id" in assigned.columns:
        for slot_id, count in assigned["slot_id"].astype(str).value_counts().items():
            if count > 1:
                violations.append({
                    "type": "duplicate_slot_assignment",
                    "slot_id": slot_id,
                    "count": int(count),
                })
    if "container_id" in assigned.columns:
        for container_id, count in assigned["container_id"].astype(str).value_counts().items():
            if count > 1:
                violations.append({
                    "type": "duplicate_container_assignment",
                    "container_id": container_id,
                    "count": int(count),
                })

    container_lookup = containers.set_index("container_id")
    slot_lookup = slots.set_index("slot_id")

    for _, assignment in assigned.iterrows():
        cid = assignment["container_id"]
        sid = assignment["slot_id"]
        if cid not in container_lookup.index:
            violations.append({"type": "unknown_container", "container_id": cid})
            continue
        if sid not in slot_lookup.index:
            violations.append({"type": "unknown_slot", "slot_id": sid})
            continue
        container = container_lookup.loc[cid]
        slot = slot_lookup.loc[sid]
        result = check_all_constraints(container, slot)
        if not result["valid"]:
            violations.append({
                "type": "placement_constraint",
                "container_id": cid,
                "slot_id": sid,
                "constraints": result,
            })
    return violations


def evaluate_solution(solution, containers, slots):
    violations = verify_solution_constraints(solution, containers, slots)
    return {
        "assignment_rate": calculate_assignment_rate(solution, containers),
        "slot_utilization": calculate_slot_utilization(solution, slots),
        "total_loaded_weight": calculate_total_loaded_weight(solution),
        "average_container_weight": calculate_average_container_weight(solution),
        "total_teu": calculate_teu(solution),
        "constraint_violations": len(violations),
    }
