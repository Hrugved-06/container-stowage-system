# RCSPPSuite Benchmark Protocol

## Purpose

This project includes a reproducible **RCSPPSuite-derived benchmark mode** so that the research evaluation is not based only on project-generated synthetic manifests.

The source XML files included in `datasets/rcspp/source/` come from three RCSPPSuite instances and their corresponding vessel profiles:

- `s_01` + `vessel_s`
- `m_01` + `vessel_m`
- `l_01` + `vessel_l`

The generated datasets are rebuilt deterministically with:

```bash
python datasets/rcspp_adapter.py
```

## Generated benchmark sizes

| Project dataset | RCSPPSuite source | Containers | Adapted positions | Seed |
|---|---|---:|---:|---:|
| RCSPPSuite Small | s_01 | 84 | 80 | 4201 |
| RCSPPSuite Medium | m_01 | 176 | 160 | 4202 |
| RCSPPSuite Large | l_01 | 460 | 400 | 4203 |

These sizes intentionally keep demand above adapted capacity so the algorithms must make non-trivial assignment decisions.

## Preserved source information

The adapter preserves or derives the fields that are actually modeled by this academic prototype:

- RCSPPSuite container ID
- 20/40-foot container type
- container weight
- port of loading (POL)
- port of discharge (POD)
- voyage discharge order
- reefer flag
- IMDG flag/type
- RCSPPSuite pseudoprofit (`Points`), mapped to the project's cargo priority
- vessel bay, row and tier
- RCSPPSuite reefer-capable tiers
- source stack maximum weight information

Every generated dataset includes `manifest.json`, recording its source instance, vessel, extraction seed, transformation rules, and excluded constraints.

## Important scope statement

This is **not a claim of full RCSPP compliance**. RCSPPSuite represents a richer industrially representative problem than the current B.E. prototype. The current optimizer does not yet implement the full RCSPP mathematical formulation, including dynamic arrival-condition evolution, ballast optimization, hydrostatic GM, trim/displacement calculations, bending moment, lashing force limits, crane constraints, paired block stowage, exact 40-foot two-half occupancy, and pairwise IMDG segregation rules.

The benchmark mode should therefore be described in the paper as:

> “RCSPPSuite-derived reduced benchmark instances adapted to the subset of cargo and vessel-position constraints implemented in the proposed academic framework.”

Do not write “full RCSPPSuite solved” unless those omitted RCSPP constraints are implemented and verified.

## Reproducible experiment command

For a quick benchmark:

```bash
python research/run_rcspp_benchmark.py --dataset rcspp_small --repeats 5
```

For all three adapted datasets:

```bash
python research/run_rcspp_benchmark.py --dataset all --repeats 5
```

The stochastic algorithms use explicit seeds. Raw run data and aggregate statistics are written to `research/results/`.

## Suggested paper wording

> In addition to controlled synthetic scenarios, the experimental framework was evaluated on reduced benchmark instances derived reproducibly from RCSPPSuite. Source cargo and vessel-position attributes were retained for the subset of constraints represented by the prototype. The adapter and extraction seeds are distributed with the implementation to support reproducibility. Advanced RCSPP hydrostatic, structural, lashing, crane, and multi-port arrival-condition constraints remain outside the present model and are identified as future work.
