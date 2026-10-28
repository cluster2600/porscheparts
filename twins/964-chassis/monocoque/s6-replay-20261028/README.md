# Finest carbon S6 torsion replay — 28 October 2026

The finest **420-section carbon monocoque case** now reproduces from the
committed S6 runner. Two independent serial CalculiX executions returned
**19,899.782469 N.m/deg**, consistent with the historical rounded value 19,900.
This closes the replay gap for this single case. It does not establish mesh
convergence, composite strength, 964/993 fitment or vehicle qualification.

| Measured quantity | Result |
|---|---|
| Original mesh | 42,747 corner nodes; 87,800 triangles |
| Quadratic S6 nodes in the printed result | 173,420 |
| Integration points | 790,200 |
| Opposing vertical forces | +1,000 / -1,000 N on the existing synthetic front patches |
| Moment arm | 1,142.608519 mm |
| Torsional stiffness, repeat 1 / repeat 2 | 19,899.782469 / 19,899.782469 N.m/deg |
| Maximum displacement magnitude | 0.977665 mm |
| Maximum clamped translation | 1.57e-22 mm |
| Relative force imbalance | 2.8662e-7, below the existing 1e-4 numerical tolerance |
| Identical repeat data | Input decks, printed displacement/reaction/stress results and parsed arrays |

The retained [validation](validation.json), [two execution records](result-after-2.json)
and [independent audit](independent-run-1.json) bind the result to its inputs.
The compressed [input deck](shell.inp.gz), [analysis mesh](model.npz) and
[parsed displacement/display-stress arrays](parsed.npz) are retained for inspection.
These arrays belong to the analysis mesh; they must not be mapped by index onto
the different PicoGK display shell in the OpenUSD bundle.

## Execution and reproduction

The unchanged `source/shell_s6.py` generated S6 elements and midside constraints.
The unchanged `source/torsion_monocoque.py` supplied the geometry and assumed
equivalent-isotropic carbon sections. CalculiX 2.21 ran locally in the existing
ARM64 image `sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4`.
Each container had a 12 GiB memory/swap ceiling, two CPU equivalents, a single
SPOOLES thread, no network and a 900-second execution deadline. Both finished;
the previously attempted 6 GiB ceiling was not reused.

[run.py](run.py) and [ccx-executed.sh](ccx-executed.sh) are exact executed
snapshots, whose original working paths are preserved in
[prepared.json](prepared.json). They are not an installed command or a general
job launcher. For an exact replay in a fresh checkout, first require that
`work/964-s6-fine-replay-001` does not exist, then create its `bin` directory,
copy the snapshots to `run.py` and `bin/ccx`, make the latter executable and run
the former with the repository root as the working directory. Do not rerun
over a retained experiment. Required Python packages are NumPy, SciPy,
Matplotlib and Shapely; the image must already exist locally.

The first launch stopped before meshing because Shapely was absent. After
installing Shapely 2.2.0 in the isolated task environment, the same script
produced both completed runs. The failed import log, full `.dat`/`.frd` files,
solver logs and raw source snapshots are also retained outside Git in the
Mac's `Developer/PicoGK/output/964-monocoque-s6-replay-20261028` archive.
The repository contains hashes of those raw files, not a claim that they are
all stored in Git.

`source/strength_audit.py::read_dat` independently parsed the printed reaction
forces and integration-point tensors. The force metric is the norm of their
total divided by 2,000 N. The existing tensor summary gives maximum/minimum
principal stresses of **42.05 / -37.96 MPa** and a maximum von Mises display
scalar of **39.93 MPa**. These are demands in an assumed isotropic model.
Allowable stress, reserve factor and `strength_pass` remain null. The separately
retained nodal `vm_output_2d` array omits bending stress and must not replace
the integration-point audit.

## Remaining engineering work

The preceding 300-section stiffness is 18,143 N.m/deg, leaving about a 9.7%
increase at the finest density. A repeat is not a convergence study. The finest
steel case, the historical bending cases and their archived fields still need
replay. The material is not a layered composite failure model; joints, inserts,
delamination, fatigue and crash behaviour remain unqualified. The 1,200 kg
vehicle target was not applied as a complete vehicle load case. Physical
interfaces, a donor torsion test and professional review are still required.
