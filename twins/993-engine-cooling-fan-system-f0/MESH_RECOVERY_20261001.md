# Fan mesh recovery — 2026-10-01

Status: new fluid mesh generated but NOT accepted for CFD; remote solver access blocked. No new airflow result or manufacturing approval.

## Findings

The archived E `checkMesh -allGeometry -allTopology` report contains 11,331 concave cells. More seriously, its rotor patch reaches x=0.1239998826 m although the nominal rotor radius is 0.1225 m and the duct radius is 0.124 m. This indicates a boundary representation problem near the tip gap, independently of convergence. A relaxed mesh gate would not fix it.

The alternative `source/build_fan_tetmesh.py` preserves separately labelled rotor, duct, inlet and outlet triangulations and constructs a conforming Delaunay tetrahedral fluid volume using Gmsh 4.15.2. The pilot holds the previous assumed 248 mm duct diameter, 360 mm domain length and 245 mm rotor. It has no wall layers and no alternator. Its output must pass the OpenFOAM extended check, surface-distance checks and mesh sensitivity before design ranking.

The 40,000-face surface failed the topology/volume-conservation assertion and was rejected. The 80,000-face Netgen attempt reconstructed the volume but stalled with 188 remaining illegal tetrahedra; it was terminated and its log preserved. A separate Delaunay run retains Gmsh's default optimization instead of that stalled Netgen pass. Signed tetrahedron quality is checked explicitly; generating a mesh is not CFD validation.

## Installed assembly remains unresolved

The newer `twins/m64-engine-system/metrology/fan-drive/metrology-report.json` still records unanchored scan scale and unknown blade count. Its scan-derived envelope must not silently replace this pilot's dimensional assumptions.

The [PMB 240 A page](https://pmbperformance.com/products/high-output-240a-alternator-for-porsche-964-and-993-90-99) and [Classic Retrofit manufacturer page](https://www.classicretrofit.com/en-us/products/porsche-964-993-240a-high-output-alternator), checked on 2026-10-01, identify the custom large-case alternator and recommend a serpentine belt with tensioner. They do not supply the dimensional drawing needed here. AS-PL's different 115 A alternator dimensions are not dimensions of this 240 A unit.

Required assembly inputs are the actual alternator housing/vents/mounting datums, support vanes and rear cone, rotor-to-casing clearances, axial stack, fan drive ratio/direction and an engine resistance curve or measured bench points. Until available, any alternator representation is a sensitivity envelope, not verified fitment or installed cooling performance.

## Compute access

The previous shared instance was absent. Dedicated Vast instance 53736084 was created using the existing approved mesh wrapper (32 effective CPU cores, RTX PRO 4000, Italy; observed running rate USD 0.342667/h excluding transfer). SSH failed because the server reported incorrect ownership/modes of its authorized_keys file. Refreshing the approved key while stopped did not repair server file permissions. The instance was destroyed and the wrapper verified its absence. No study inputs reached that machine and no remote CFD ran.

The Mac has no running Docker daemon or OpenFOAM executable. Local meshing can proceed, but OpenFOAM execution requires restoring an accessible solver environment. The Vast browser console was left at login for the user; no credentials were retrieved or authentication protections weakened.

## Next acceptance steps

1. Check the new fluid mesh in OpenFOAM without lowering thresholds, and quantify rotor surface deviation and retained tip gap.
2. Resolve wall-layer/y+ treatment and compare at least three meshes before ranking blade shapes.
3. Run the reference and controlled variants at matched RPM and downstream pressure, reporting flow, torque, power and convergence windows.
4. Add verified stationary assembly geometry and validate against bench data before claiming installed improvement.

## Completed local result

The Delaunay run completed with **355,404 tetrahedra** and a minimum signed inverse condition number of **0.00034333** (positive, but very poor). Gmsh still reports **394 ill-shaped tetrahedra**. This is a rejected candidate for design ranking, not a repaired/qualified CFD mesh. The source was the local E reproduction, identified by SHA-256 in the [manifest](results/mesh-recovery-20261001/manifest.json); it is not claimed byte-identical to the previous remote generation.

The simplified rotor volume is 301,782.425 mm³ versus 301,810.315 mm³ for its source (approximately 0.0092% difference). A volume match alone cannot establish surface fidelity. Logs and the compute teardown receipt are under [results](results/mesh-recovery-20261001/).

Reproduce in an environment with Gmsh 4.15.2, NumPy, Trimesh and fast-simplification:

```sh
python source/build_fan_tetmesh.py /absolute/path/rotor-mm.stl /absolute/path/new-output --faces 80000
```

The output folder must be new. This command only generates and audits a fluid mesh; it does not launch a solver.

The deterministic bidirectional surface audit (2,000 area-weighted points per direction, seed 993) found a maximum sampled deviation of **0.0661 mm** and a minimum simplified-vertex radial clearance to the analytic cylinder of **1.4850 mm**. These are sampled surface checks, not a Hausdorff bound, a physical tolerance or a full clearance check against the faceted duct. See the [audit](results/mesh-recovery-20261001/surface-distance-audit.json).

Raw mesh and original logs: [research archive](https://github.com/cluster2600/porscheparts/releases/tag/fan-mesh-recovery-2026-10-01). The 9.1 MiB package has SHA-256 `9d5be999b1474e4adaa93ec713e07c457bee4a3a3e4dc23f74b89e786f9ef31c`. Three existing fan-sweep tests passed; strict documentation-link and staged whitespace checks passed. Full repository check status is recorded separately in the archived check log.

Full `make check` completed the main Python suite with **3,259 tests, 152 skipped, no failures**, plus the next 10- and 7-test checks. It then stopped at `917-manufacturing-f37-lpbf-audit-check` because the local Docker daemon is unavailable. Thus the overall repository check exited 2 and is **not fully passed**. The [complete log](results/mesh-recovery-20261001/make-check.log.gz) preserves this environment blocker.
