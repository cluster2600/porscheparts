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
added-BCC experiment. No cellular candidate, eligible-volume fraction or mass gain
has been numerically accepted by this continuation.
