# Replay and retained execution evidence

Use the complete repository at the published revision, the private input
capsule and its manifest, and a **new** output root. Never run a writer inside
the frozen capsule. All Python arrays use `allow_pickle=False`. Units are mm.
The delivery is a mesh/recipe master, with no new analytic solid CAD claim.

## Exact construction

1. Verify the original OBJ, decoded source arrays, frozen fine envelope,
   parent manifest, source plane fits and rigid frame against `results.json`
   and private `input-admission.json`. Plane equations/selections stay private.
2. Build `source/clip_head.cpp` with native CGAL 6.2.1, GMP/MPFR and C++17.
   `source/run_clip.py --help` documents its explicit inputs. Its actual run
   and cube/empty-result/refusal controls are retained in `execution.json`
   and `controls/`. The global three-plane candidate is a rejected trial.
3. For each of the three rows in private construction hypotheses, write a
   separate plane file (first line `1`, then its four negative-halfspace
   coefficients). Run `clip-head vertices.f64le faces.i64le 4304104 8614076
   plane.txt NEW_CASE/candidate` on the unchanged parent arrays. Actual commands,
   terminal status and native output hashes are in `single-plane-cases/{0,1,2}/`.
4. Run `source/assemble_single_plane_local.py --parent FINE.npz --cases CASES
   --planes HYPOTHESES.json --plan local-cut-plan.json --output NEW_LOCAL`.
   It verifies exact intact-face membership, full partial-triangle containment,
   cap ownership and disjoint selections before writing source provenance.
   It does not use the plan's superseded global-mesh construction sentence.
5. Run the unchanged `../935-hypothesis-study-20261029/source/validate_build_final.py`
   on the local source mesh. `source/check_contacts.py --help` describes the
   exact shared-simplex proof for raw contact findings. Preserve both receipts.
6. `source/prepare_aligned.py --help` lists the checksum-bound reports, frame
   and plane inputs. It admits the source mesh and writes the rigid build mesh.
   Run the unchanged full geometry validator again on this actual aligned mesh.
   Its raw intersection count is zero for the delivered revision.
7. `source/export_three_mf.py --help` describes the preferred exact-coordinate
   3MF export and readback. Actual executed argv for steps 5–8 are retained in
   `local-delivery-execution.json`.

## Supports and all contours

8. `source/prepare_supports.py --mesh BUILD.npz --report ADMISSION.json --output
   NEW_SUPPORTS` regenerates the exterior grid and support assumptions. Run
   the unchanged `build_component_3mf.py BUILD.npz ADMISSION.json HYPOTHESES.json
   NEW_COMPOSITE` from the earlier study's source directory. All mesh resources
   and graph/overlap checks must pass.
9. Build `source/slice_hypothesis.cpp` with the same CGAL exact kernel. Retain
   the cube, tetrahedron, tangent and refusal controls before the actual full
   mesh. The working binary inputs are little-endian f64 vertices and i64
   triangles; layer planes use exact decimal 0.05 mm. Native stdout and
   `local-slicing/native.json` retain the actual full slice counts and timing.
10. `source/format_cli.py --help` documents fixed-decimal normalisation without
    changing vertex order. Use the unchanged `validate_cli_readback.py` on the
    exported head CLI, its actual surface volume and layer interval 0.05 mm.
11. `source/union_local_layers.py HEAD.cli HYPOTHESES.json NEW_UNION --workers 4`
    performs independent Clipper/GEOS union checks on every declared layer.
    Run the unchanged `validate_cli_readback.py` on its exported CLI with
    `--volume-mm3` equal to the independent layer integral from the union
    receipt, `--layer-mm .05` and
    `--volume-reference-kind independent-layer-integral`. The head-only check
    uses the actual 3D surface volume instead. Neither check is a machine job.

## Fidelity, cross-host checks and packaging

12. `source/assess_local_fidelity.py --help` lists the parent, provenance, exact
    scan arrays and local mesh inputs. Keep both complete 100,000-sample
    directions and the unconditioned parent comparison. No sample is excluded
    because of the provisional component interpretation.
13. On owner Kali1/ext4, compile `source/check_indexed_mesh.cpp` with
    `g++ -std=c++17 -O2 -Wall -Wextra`. Its private `run_remote.py` pins the
    source and actual aligned NPZ, performs analytic/negative controls and
    writes terminal execution/runtime/manifest receipts. Compare decompressed
    vertices/faces to Mac SHA-256 values before accepting cross-host agreement.
    The recovered JSON receipts and verified remote manifest remain in
    `kali-verification/`; this checker does not test self-intersections.
14. `source/package_delivery.py NEW_CAPSULE REPOSITORY` verifies the exact
    admitted revision, all export/readback gates and cross-host byte identity
    before packaging. It refuses existing delivery or frozen output. The
    expected revision hash is intentionally fixed, so another geometry needs
    an explicitly reviewed companion package script and fresh results.

The rejected global assembly, float32 STL, PicoGK output and initial numerical
containment calculation remain reproducible trial evidence. Their files are
not substituted for the local delivery. Isolated native/runtime bytes and
downloaded wheels stay private; public source and aggregate hashes are in Git.
This runbook describes executed construction and checks, not physical or
manufacturing qualification and not a completed physics chain.
