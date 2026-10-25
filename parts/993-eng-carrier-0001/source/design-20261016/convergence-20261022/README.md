# Carrier refinement and real CUDA checks — 22 October 2026

Results, images, acceptance limits and refusals are in the
[English report](../../../../../docs/reports/carrier-convergence-20261022/README.md).
All commands run from the repository root. Python requires NumPy; rendering also
requires Matplotlib. Native solver execution requires Linux and the exact qualified
CalculiX binary. Large working artifacts stay under `work/`.

## Retained inputs

- R2 reference: `../resume-20261020/picogk-R2-study/surface.mesh64.gz`, decompressed SHA-256
  `396161993b35f708fdd1e527f875aff60daf8c79031dc9a39c42891a9c1ae1a0`.
- Existing coarse geometry, mapping proof, consistent bore loads and material:
  `work/carrier-resume-20261020/meshlib-R2-{quadratic-geometry,quadratic-mapping-audit,matched-traction}-001/`.
- Study parameters: `work/carrier-resume-20261020/picogk-R2-mechanics-study.json`.
- Declared criteria: `docs/reports/carrier-convergence-20261022/convergence-contract.json`.

These are retained inputs, not inferred measurements. Recreate missing coarse
work artifacts with the [preceding workflow](../resume-20261020/README.md).
Always use a fresh output directory. Reports bind their actual inputs by SHA-256.

## Mechanical sequence

1. `refine_matched_tetrahedra.py` splits certified coarse cells into eight using
   shared original midpoints. `refine_by_cell_centres.py` provides the distinct
   four-way interior fan, preserving the original surface facets.
2. `export_volume_boundary.py` exports the **actual prepared volume boundary**.
   Run the preceding exact orientation/connectivity audit against this boundary;
   an old boundary file cannot certify the red8 volume.
3. `prepare_refined_quadratic.py` or `prepare_fan_quadratic.py` creates shared-edge
   T10 nodes. The preceding `audit_quadratic_mapping.py` certifies every mapping.
4. `prepare_refined_quadratic_loads.py` integrates the original constant tractions
   over red8 child facets. For the unchanged fan boundary, the preceding
   `prepare_matched_traction_cases.py` is reused; verify exact original patch
   metadata and traction-vector equality before solving.
5. Run analytic controls on the exact native binary. Then use
   `run_native_ccx_serial_results.py`: parallel assembly/factorization with
   `CCX_NPROC_RESULTS=1`. The original `run_native_ccx.py` is retained to reproduce
   the refused full-size parallel-recovery case, not as the production profile.
   For a fully serial diagnostic, pass `--threads 1`. The distinct
   `prepare_iterative_solver.py --preparation <verified-preparation> --output <fresh>`
   changes only the static linear solver to built-in iterative Cholesky.
   Its analytic controls and reference-field repeat must pass before using it
   for a finer production solve; no alternative-backend success is implied.
6. `assess_native_P1.py` / `assess_native_P2.py` require an actual completion
   receipt, input/output identities, complete rows and equilibrium. P2 includes
   independent stress-energy integration. P1 also requires the preceding
   `check_stress_strain_energy.py` on the complete field.
7. `compare_accepted_fields.py --cases <case-list.json> --output <fresh.json>`
   computes full-field peaks and volume-weighted percentiles. Each case contains
   `label`, `preparation`, `assessment` and, for P1, `energy` paths. Compare spatial
   refinements at a fixed element order. An interior fan is not uniform `h/2`.
8. `render_convergence.py --comparison <comparison.json> --output <media-dir>`
   generates the measured comparison figure and its provenance.

Failed orientation, geometry, equilibrium, energy, volume or runtime limits remain
failures. A timeout has no mechanical field credit. No acceptance limit is fitted
to the observed result.

## Warp sequence

`prepare_carrier_warp_oracle.py --help` prepares the deterministic complete-carrier
fixture and independent libigl distances. Its dependency lock is
`requirements-libigl-x86.txt`; it is separate from Warp's hash-pinned requirements
in `containers/warp-geometry.requirements.txt`.

On the actual GPU, run the unchanged `benchmarks/warp-geometry/pilot.py` synthetic
fixtures and tests, followed by `check_carrier_warp.py` for both `cpu` and `cuda:0`.
Supply `--pilot`, `--bundle`, `--oracle-report` and a fresh `--output` directory.
The evaluator refuses a CUDA request that does not resolve to an actual CUDA
device. `render_warp_validation.py` plots the paired results.

## Paid runtime ownership

Use only the existing approved OpenBao provider wrapper. Keep launch/endpoint
receipts and SSH material outside Git. The executed rental is bounded to one hour
and USD 2, including its recorded transfer allowance. Run `lease_guard_live.py`
**in a retained foreground execution session**, then verify its heartbeat and
exact provider ownership. A detached child from a short-lived tool command did
not survive reliably; the original `lease_guard.py` remains historical evidence.
Collect complete outputs, verify their hashes, destroy the exact owned instance,
and independently confirm its absence. Transport loss is not solver failure or
proof of provider teardown.

## Further cellular optimization

Replace eligible solid material; filling existing hollow arms increases mass.
The report describes the current nominal thin walls and the earlier, different
added-BCC experiment. The executed conservative whole-cell screen selects 543.712 mm³ of the analysis
volume, with a conditional 1.442 g saving at relative density 0.40. This is a
subset screen, not a maximum saving or a generated and solved lighter part.

`prepare_cellular_screen.py` requires the accepted complete quadratic field,
its mapping proof, independent energy assessment and source hashes. It integrates
all cell energies and constructs an independent libigl distance oracle for all
cell centroids. Run the unchanged `check_carrier_warp.py` separately on CPU and
actual CUDA; then `select_cellular_budget.py` consumes both reports and
`cellular-screen-parameters.json`. Keep arrays outside Git and publish compact
receipts and the generated figure. The whole-cell radius, curved mapping and
transport allowances protect the entire selected cell; centroid clearance alone
is insufficient.

`build_native_thread_profiles.sh` builds pinned Debian 2.21 source with default
and recursive Fortran storage. `run_native_ccx_alternate.py` requires the expected
binary SHA before creating a case. The recursive eight-thread T4 regression
passes the original analytic, equilibrium, energy and declared full-field
comparison limits; the quadratic attempt failed its 24 GiB allocation cap.
`run_native_ccx_long_serial.py` is the distinct one-thread, at-most-2,400 s worker.
The executed 2,349 s fine T10 repeat timed out and contributes no result.


## Imported-volume quality optimization (25 October)

The existing Gmsh 4.15.2 geometry runtime runs `optimize_tetrahedra_gmsh.py` with
`--mesh`, its `--expected-sha256`, a fresh `--output`, and `--method` (`default`,
`Netgen`, or `Relocate3D`). Three iterations and two requested threads are fixed.
The worker records only a floating-point boundary checkpoint. It does not admit
a mesh mechanically; the complete indexed/exact audit remains mandatory.

**Netgen appends a second cell block in the exercised discrete import. Never use
the combined output as a volume.** The independent audit refuses its doubled
volume and nonmanifold faces. `extract_appended_netgen.py --original ORIGINAL.npz
--combined COMBINED.npz --expected-original-sha256 ORIGINAL_SHA
--expected-combined-sha256 COMBINED_SHA --output FRESH` verifies all original
prefixes and boundary entries before explicit extraction. It refuses a changed
prefix rather than guessing a partition. Keep both original and refused outputs.

Run the unchanged `../resume-20261020/audit_wildmeshing_volume.py` with `--mesh`,
`--boundary` and fresh `--output` using the isolated geometry runtime. Separately
run `tetra_quality_diagnostics.py` on every cell. The extracted carrier block
passes exact orientation/connectivity and improves minimum mean ratio from
0.00347694 to 0.0160222. Its future T10 conversion, mapping/transport audit and
new mechanical fields remain required. `render_mesh_quality.py` consumes the
reference and candidate quality reports to reproduce the figure. The full
report records all intermediate hashes, tests and refusals.


`prepare_remeshed_quadratic.py --volume VOLUME --exact-audit EXACT_AUDIT
--reference-geometry REFERENCE_GEOMETRY --reference-mapping REFERENCE_MAPPING
--output FRESH` is the distinct replacement-connectivity conversion. It verifies
the complete oriented boundary against the retained linear surface, preserves
its source-bound distance allowance, and rounds the inherited sum upward.
It does not claim a new nested refinement. Run the unchanged
`../resume-20261020/audit_quadratic_mapping.py` on its fresh geometry, followed by
`prepare_matched_traction_cases.py` with the same material/load study. Before any
solve, compare all bore patches and traction vectors with the retained P1/P2
preparations; equality holds in the executed replacement case.


## Native Apple Silicon solver

`build_macos_ccx.py --output FRESH` is the executed clean-replay installer for
GCC 16.2.0 / ARPACK 3.9.1 already present on the Mac. It verifies all four source
archive hashes, rejects unsafe archive members, applies the Debian CalculiX
patches plus official SPOOLES `I2Ohash-64bit.patch`, and retains compiler logs.
The compatibility edits follow the linked macOS recipe; the additional hash
patch is essential for the demonstrated large case. No global package is changed.

Compile `spooles_hash64_control.c` with `-fsanitize=undefined
-fno-sanitize-recover=undefined`, the selected source include directory and its
static SPOOLES library. The unpatched source fails on the large hash keys; the
patched source passes insertion, lookup and removal. Source build alone remains
unqualified until the existing analytic controls and full reference pass.

`run_local_ccx_serial.py` takes `--binary`, `--expected-binary`, `--deck`, optional
`--mesh`, fresh `--output`, `--seconds` (at most 1200) and `--rss-gib` (at most 24).
It records the actual solver PID, one requested thread, a child CPU limit, a wall
bound, sampled RSS, reaping and complete file identities. Its sampled memory
ceiling is not an OS address-space cap. The worker's Darwin exit-race regression
is covered separately; a historical finished log without a terminal receipt stays
refused. Use the existing `assess_native_P1.py` / `assess_native_P2.py` readers
and independent P1 energy checker before comparing fields.

### Large quadratic parallel-recovery gate

`run_native_ccx_long_parallel.py` is the bounded recursive-binary profile with
parallel assembly/factorization and **`CCX_NPROC_RESULTS=1`**. It requires the
expected binary SHA and a fresh directory, records the requested result-thread
count, limits wall time to 2,400 s and virtual address space to at most 240 GiB,
and retains the actual terminal receipt and output hashes. The executed memory
limit must fit the measured cgroup allocation and leave collection time before
the fixed lease deadline. It does not change loads, geometry or acceptance limits.

The recursive binary with eight result-recovery threads passed the analytic
controls but **failed the complete 381,564-cell T10 reference** on Linux: force
residual 3,795.43 N and relative independent-energy residual 48.19. A normal exit
and a `Job finished` marker do not admit that field. Serial result recovery must
pass the fresh analytic controls **and** the full reference comparison before
launching a fine production case. See the cumulative report for actual receipts;
the existence of this profile is not itself a successful fine solve.

`render_quadratic_displacement.py` requires a complete accepted T10 assessment
and matching geometry/result hashes. It displays all T6 boundary faces as four
triangles each, with deformation amplified tenfold. Surface colours average
nodal displacement magnitudes for display; they do not smooth stress peaks.


The first 4,884,701-node replacement-mesh T10 attempt timed out at its declared
2,215 s wall limit with an empty DAT. The separate
`run_native_ccx_extended_parallel.py` retains the same numerical binary and serial
recovery, allows up to 7,200 s and adds `stdbuf` line buffering. Pair it with the
new `lease_guard_extended_live.py` only after recording a fresh, at-most-three-hour,
USD 2 lease and checking its actual provider quote and memory allocation. Use
resumable, checksum-verified collection inside the original deadline; do not
extend an existing lease or interpret a timeout as a converged field.

The extended eight-assembly/one-recovery profile later failed the complete
reference on another host despite passing the analytic controls. Its fields are
excluded; neither buffering nor the host change alone is an established cause.
Prefer the separately recorded `run_native_ccx_solver_parallel.py` trial:
assembly and recovery stay serial, SPOOLES threading is selected independently,
and preload/buffering environment variables are removed. Its hard maximum is
10,800 s; two full reference repetitions and the original analytic controls must
pass before a fine run. The new `lease_guard_four_hour_live.py` bounds a fresh
lease to four hours / USD 2 without extending any earlier deadline.

`inspect_linux_limits.py` reads actual finite cgroup v1/v2 limits; unknown or
unlimited values stay null. Require a successful hardware and bidirectional
checksum-verified bulk-transfer probe before installing or executing a solver.
