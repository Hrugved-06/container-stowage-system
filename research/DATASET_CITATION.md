# Dataset provenance and citation

The public benchmark extension in this repository is derived from **RCSPPSuite (Representative Container Stowage Planning Problem Suite)** supplied with the project research materials.

The suite documentation attributes the benchmark to:

> Sivertsen, A., Reinhardt, L., & Jensen, R. M. (2024). *A representative model and benchmark suite for the container stowage planning problem*. Transportation Science (listed as under review in the supplied RCSPPSuite documentation).

Related recent work using the representative benchmark suite includes:

> J. van Twiller, A. Sivertsen, R. M. Jensen, and K. H. Andersen, *An Efficient Integer Programming Model for Solving the Master Planning Problem of Container Vessel Stowage*, 2024.

## How this repository uses the suite

This repository does **not redistribute or claim results for the full 73-instance RCSPP formulation**. It includes the three source instances and vessel profiles used to generate the reduced benchmark datasets (`s_01`, `m_01`, `l_01`) together with a deterministic adapter and provenance manifests.

In a paper, describe the evaluation as **RCSPPSuite-derived reduced/adapted benchmark instances** unless the full RCSPP constraints are implemented.
