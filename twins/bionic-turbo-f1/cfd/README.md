# Compressible comparison of the cold side

This chain prepares the **conceptual compressor and its hypotheses**, with the
supplied surfaces of its wheel and volute, for OpenCFD 2406 `rhoSimpleFoam`.
The geometry is not replaced by an equivalent rectangular duct.
No measured turbo map or physical calibration is claimed.

The only supported image is the official OpenCFD ARM64 runtime, pinned
in `prepare_case.py`. Version 2406 includes the MRF pressure work in
[the official energy equation](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoSimpleFoam/EEqn.H).
Foundation 13 is not a supported run profile here.

Input: an ASCII STL in metres, with exactly four regions `inlet`,
`outlet`, `rotor`, `stator`, whose combined edges close a consistently
oriented surface. The generator must document the idealised seals and
the excluded leakage paths. This check verifies neither self-intersection, nor clearance,
nor the presence of the seed point in the fluid. Independently verify the point
`(0.015, 0, 0.040)` before meshing. The inlet is a Z plane above the rotating
zone and the outlet a Y plane beyond it. The bounds come from the STL.

The rotating zone has a radius of 32 mm and extends from Z = -4 to +33 mm. All
faces of the wheel must belong to it; the two measurement sections must
remain outside it. The hypothetical initial conditions are: inlet total
pressure 101325 Pa, inlet total temperature 298.15 K, speed of
100000 rpm about +Z and outlet **static** pressure 121590 Pa.
The pressure-ratio option denotes outlet-static/inlet-total, not
the total/total ratio.

```sh
python twins/bionic-turbo-f1/cfd/prepare_case.py \
  work/domain/shell.ASCII.stl work/cfd-baseline-coarse \
  --level coarse --rotation-sign 1 --pressure-ratio 1.2
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage config
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage mesh --timeout 600 --cpus 4 --memory-gb 12
python twins/bionic-turbo-f1/cfd/run_case.py work/cfd-baseline-coarse --stage solve --timeout 1800 --cpus 4 --memory-gb 12
python twins/bionic-turbo-f1/cfd/audit_case.py \
  work/cfd-baseline-coarse work/cfd-baseline-coarse-audit.json
```

Each case, step and report refuses overwriting. Rejected attempts remain
available; any modified configuration receives a new directory. The runner
uses only the local image, without network, with explicit limits on
CPU, memory and duration. `coarse`, `medium`, `fine` set the background cells to
1.6, 1.2 and 0.9 mm. A refinement box imposes level 1 throughout the retained
fluid volume: nominal sizes 0.8, 0.6 and 0.45 mm. This box creates
no boundary; the four patches come from the STL alone.

The targeted `medium-gap` trial adds the gap refinement of the
[official OpenCFD 2406 tutorial](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/tutorials/mesh/snappyHexMesh/gap_detection/system/snappyHexMeshDict):
`gapLevel (4 1 3)`, `gapMode mixed`, `gapSelf true`. The target is four cells,
with a level-3 ceiling; detection includes faces of the same STL. The
`mixed` mode examines both sides of the surfaces, without assuming that the normals
of the obstacles and those of the envelope designate the same material side.
For `medium`, the minimum nominal size of 0.15 mm corresponds to 3.33 cells
in the 0.5 mm wheel/nut gap and 4.27 in the rear gap of about 0.64 mm.
The ceiling may therefore prevent reaching the four-cell target. The
`coarse` and `fine` profiles cap at 0.2 and 0.1125 mm respectively; `coarse` does not aim
for three cells in 0.5 mm. These ratios are estimates before snapping,
not measured counts nor proof that the gaps are resolved. Local refinement
transitions reappear and remain subject to the same quality
checks. Snapping remains constrained to the original STL region.
The native threshold of six million cells is approximate: a pass may
exceed it or interrupt refinement before its requested level. The container
memory limit and the run timeout remain independent. There is currently
**no prismatic wall layer**. These meshes serve as numerical
pilots; boundary-layer resolution remains to be qualified.

Before any solver, the extended check `checkMesh -allTopology -allGeometry`
must succeed. The number of closed shells, computed by exact edge
adjacency, the regions present on each shell and the global and per-shell Euler
characteristics must remain identical to the input STL.
This check notably detects an isolated wheel wrongly connected
to the housing when meshing a gap that is too narrow. The native expression
"closed singly connected" does not replace this count. Equality of these
invariants does not constitute a demonstration that the shape and
dimensions of all passages or gaps are preserved.
The comparison with the STL does not validate its construction either: spurious
passages introduced upstream must be rejected by an independent geometric
contract, before any mesh preparation.

The audit links the histories to the prepared inputs and to the inspected mesh. It
requires complete and continuous histories, the expected signs at the sections,
mass conservation, absolute impermeability of the walls, limited backflow,
stability of flow, torque and energy, positive pressures and temperatures
and low residuals. The total enthalpy flux uses
`sum(phi*h) + 0.5*sum(phi*magSqr(U))`, with the absolute velocity and sections outside
the MRF. It must equal **minus** the angular velocity multiplied by the
moment of the fluid on the wheel; no absolute value masks a wrong sign.

An accepted history does not rank performance. The comparison requires
a common wheel, seal hypotheses, inlet/outlet extensions and service
conditions, then a sensitivity study on the mesh and
the wall treatment. A single point at imposed back-pressure demonstrates
neither maximum flow nor sonic choking. No efficiency is deduced from the
incompressible approximation `p + rho*U²/2`. Steady iterations do not
represent a physical spin-up time. Engineering validation
and manufacturing authorisation remain false.
