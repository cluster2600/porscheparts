# Finest carbon S6 bending replay — 28 October 2026

Two serial CalculiX 2.21 runs of the existing 420-section carbon case returned
**8,828.496848 N/mm**, with **14,611.652520 N/mm** for the cabin sag metric.
They reproduce the historical rounded values 8,828 and 14,612 in
`derived/bending.json`. The analysis mesh has exactly the same coordinates and
triangles as the [torsion replay](../README.md).

| Measured quantity | Result |
|---|---|
| Applied load | 2,000 N downward, area-weighted over 573 existing sill nodes |
| Vertical support nodes | 106, on the original synthetic axle strips |
| Corner / quadratic nodes | 42,747 / 173,420 |
| S6 elements / integration points | 87,800 / 790,200 |
| Stiffness, both repeats | 8,828.496848 N/mm |
| Cabin stiffness, both repeats | 14,611.652520 N/mm |
| Maximum displacement magnitude | 0.286053 mm |
| Maximum fixed translation | 8.10e-22 mm |
| Relative external-force imbalance | 3.4481e-8, below the numerical tolerance 1e-4 |
| Identical between repeats | Input decks, printed fields and parsed arrays |

The [validation](validation.json) binds the [input deck](shell.inp.gz),
[mesh and load arrays](model.npz), [parsed fields](parsed.npz),
[execution record](result-after-2.json) and [independent audit](independent-run-1.json).
`source/strength_audit.py` parsed all printed nodes and integration-point tensors.
RF includes applied loads as well as constraint reactions; its total is tested
against zero. Moment equilibrium has not been qualified. The maximum/minimum
principal stresses are 21.01 / -35.11 MPa; maximum von Mises is 26.80 MPa.
These are demands in an assumed equivalent-isotropic material. Allowables,
reserve factors and strength acceptance remain null. The nodal `vm_output_2d`
array omits bending stress and cannot replace the integration-point audit.

The [driver](run.py) and [Docker launcher](ccx-executed.sh) are exact executed
snapshots, not an installed command. They reuse the unchanged `bending.py`,
`torsion_monocoque.py` and `shell_s6.py` helpers. Before reproducing, require a
fresh `work/964-s6-bending-replay-001` directory, stage these files as `run.py`
and executable `bin/ccx`, and stage the public torsion `../model.npz` at
`work/964-s6-fine-replay-001/model.npz` if that reference is absent. Never
overwrite an existing experiment. Run from the repository root with the
Python dependencies recorded in the validation and the pinned image available.
Each solver container used a 12 GiB memory/swap ceiling, two CPU equivalents,
one SPOOLES thread, no network and a 900-second deadline. Both completed.

Full raw files and logs were copied and hash-verified outside Git in
`Developer/PicoGK/output/964-monocoque-s6-bending-replay-20261028` on the Mac.
The public compressed input and parsed arrays permit inspection without those
large raw files. These arrays belong to the analysis mesh, not the different
PicoGK display mesh in the OpenUSD bundle.

This closes only the finest carbon bending replay. It does not replay the
steel, open-shell or member-removal cases, establish convergence, validate
composite failure or apply a complete 1,200 kg vehicle load case. Measured
interfaces, process data and physical correlation are still missing.
