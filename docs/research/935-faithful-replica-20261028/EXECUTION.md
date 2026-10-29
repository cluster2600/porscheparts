# Execution report — faithful 935 head, 28 October 2026

**Observed scan surfaces were preserved and checked. A complete CAD replica,
validated head simulation and print-ready metal job were not achieved.** Missing
physical inputs prevent those qualifications. This task spent USD 0 on Vast and
created no instances. Publication does not close the engineering gates.

## Executed geometry work

- Rehashed the full original on Mac and Kali1:
  `4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486`.
- Native Kali1 audit: 28.52 seconds; 1,281,608 vertices, 2,466,040 triangles,
  99,876 open edges, no edge with incidence above two, eight zero-area triangles
  and four connected surface components. Self-intersections were not evaluated.
- Exported the largest component (2,458,749 triangles, still including attached
  studs) and preserved other components separately. Seventeen-digit OBJ export
  followed by reload preserves Float64 coordinates and triangle connectivity
  exactly. No smoothing, decimation or hole filling was applied. Numerical equality
  does not establish scanner accuracy.
- Saved open-edge segments as NPY and generated XY/XZ/YZ inspection views.
  Functional openings and scan gaps have not yet been distinguished.
- Compared the prior 300k mesh with 2,000 seeded surface samples in each direction:
  P95 0.060583 OBJ unit from reference to candidate and 0.058635 in reverse;
  maximum sampled distance 0.138191. These are neither millimetres nor certified
  Hausdorff bounds nor accepted engineering tolerances.
- Retrieved seven audit files from Kali1 and verified every SHA-256 against its manifest.

## Actual software-chain status

| Tool | Current-run evidence | Limit |
|---|---|---|
| Installed Qwen adapter | Loaded and queried; proposed unsupported cylinder dimensions, rejected with `Numeric bounds` | No model-generated geometry/code executed; not admitted for this reconstruction |
| Native PicoGK on Kali1 | Bundle hashes, native witness and demonstrator passed; approximately 232 MB peak memory | Runtime check only; no head voxel reconstruction |
| Scan audit | Exact surface export, topology counts and sampled deviation maps executed | Observed surfaces only; units unverified |
| Gmsh | Version 4.12.1 executed in the extracted environment | No head volume mesh generated |
| OpenFOAM 13 | Analytic Poiseuille on three meshes, two repetitions; all existing contract criteria passed with identical canonical metrics | Synthetic case, not head CFD; full extracted-image integrity was not reverified |
| CalculiX | Reference chain located | No head analysis: geometry, loads and material remain insufficient |
| Adamantine | Existing benchmark and corrections located on Kali1 | Not rerun here; no head LPBF simulation or manufacturer process data |

OpenFOAM used an existing read-only rootless extraction with network isolation and
one writable case directory, without Docker. Transferred benchmark sources match
this run's local sources by hash. This is not a new full-image integrity attestation.
The first launch failed because `/case` was absent from the read-only root; a new
attempt used the existing `/workspace` mount point and completed. Both logs remain private.

The seller's 11 October email was reread: Xtreme, cast then machined, with no scale,
internal drawings or engine loads supplied. Private correspondence is not published.

## Deliverables and reproduction

Heavy/private artifacts remain outside Git under `work/935-faithful-20261028/`:

- `audit-001/observed-main-with-attached-hardware.obj`: main observed surface, **not print ready**;
- `audit-001/observed-other-components.obj`: remaining observed components;
- `main-source-face-indices.npy` and `boundary-segments-source-units.npy` in that audit directory;
- two deviation CSVs, `audit.json`, `manifest.json`, and the separate `audit-views.png`;
- PicoGK/Qwen/OpenFOAM results, environment versions and test logs;
- `935-observed-surfaces-NOT-PRINT-READY.zip`, 54,604,105 bytes, with 26 verified payload files.

That private archive predates the English publication pass and contains the original
French documentation. It is an immutable execution snapshot, not the current English
GitHub dossier. Archive SHA-256:
`c789afc6b657768522d6692970827982905e25762c7f99677acb6185b1126fe9`.

Published implementation:
[auditor](../../../scripts/audit_935_faithful_scan.py),
[inspection renderer](../../../scripts/render_935_scan_audit.py),
[direct dependencies](../../../scripts/935-faithful-requirements.txt),
[focused tests](../../../tests/test_935_faithful_scan.py).
The frozen [execution record](execution-20261028.json) records source-code and output
hashes from the execution, separately from later documentation edits.

Use Python 3.12 with the listed dependencies, the authorised original OBJ, and a new
output directory. The dependencies are direct version pins, not a complete wheel-hash
lock. The private `kali-environment-and-tests.txt` records installed transitive versions.

```sh
python scripts/audit_935_faithful_scan.py "$SOURCE_OBJ" "$NEW_OUTPUT" \
  --contract docs/research/935-faithful-replica-20261028/baseline-contract.json
python scripts/render_935_scan_audit.py "$SOURCE_OBJ" "$NEW_OUTPUT" "$NEW_OUTPUT/views.png"
python -m unittest discover -s tests -p test_935_faithful_scan.py -v
```

The auditor rejects an unexpected source hash and an existing output directory.
Add `--candidate PATH_TO_PLY` for a bidirectional sampled comparison. The audit
manifest covers audit outputs; the separately generated plot has its own hash in the
execution record. The OBJ exports are surface references, not editable parametric CAD.

## Validation, budget and open gates

At execution revision `bae99f72`, `make check` passed: 614 tests, 11 skipped. Four
skips were the new audit tests in the Mac environment without its dependencies;
those four tests ran successfully on Kali1 with no skips. This historical result
does not establish a passing suite on the newer publication base; publication
validation is recorded in [publication-validation.json](publication-validation.json).

All twelve [input packages](baseline-contract.json) remain incomplete. Critical
requirements include verified units and three independent specimen measurements,
interface tolerances, complete internal geometry, donor identity/loads, material
and process data. Blindly closing 99,876 open edges could seal functional passages.
A larger GPU cannot supply these measurements.

The [China dossier](CHINA_MANUFACTURING.md) compares suppliers and contains an unsent
technical enquiry. No supplier message, scan transfer or order was made. Budget:
USD 30 compute plus USD 5 transfer/teardown reserve, USD 35 total; task spend remains
zero. The budget is an instruction, not an automatic billing controller. No paid
compute was justified for the work executed so far.
