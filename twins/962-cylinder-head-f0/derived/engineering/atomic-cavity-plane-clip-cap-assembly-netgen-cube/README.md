# Netgen on a saved toy cube

**The saved-cube software fixture completed and passed its own SICN ≥ 0.1 gate.** This capsule contains two generated toy cube meshes, complete tiny arrays, source, guards and closed evidence. It contains no cylinder-head geometry and grants no head optimizer or physical qualification.

| Complete cube observation | Before Netgen | After Netgen / saved reopen |
| --- | ---: | ---: |
| Referenced nodes | 42 | 15 |
| Referenced interior nodes | 34 | 7 |
| Linear tetrahedra | 191 | 40 |
| Orphan nodes | 0 | 0 |
| Native minimum SICN | 0.027175498119979526 | 0.4780600202533193 |
| Native SICN < 0.1 | 8 | 0 |
| Nonpositive native SICN | 0 | 0 |
| Exact oriented exterior triangles | 12 | 12 |
| Opposite internal face pairs | 376 | 74 |
| Independent summed volume (mm³) | 343 | 343 |

The exact [fixture report](reports/fixture-report.json), SHA256 7d6f638b20388348810ea564e6fa7ffcdd2c5555fcbdc6d0d2c792e3d42defb7, records completed_cube_only. Runtime is pinned macOS ARM64 Python 3.10.11 / NumPy 2.0.2 / Gmsh 4.15.2. One root-controlled native run returned RC0 with no stop: 0.145127125 s worker, 0.714051375 s controller, 0.908242625 s outer. Root before/after checks retained all 39 child pins and three runtime identities.

The controller acceptance window is 30 seconds, with sampled 1 GiB RSS, sampled 16 MiB output and two software threads. Two RSS samples were saved privately, maximum observed 135,168,000 bytes. These are sampled observations, not certified peaks or hard OS RAM/CPU quotas. There was no automatic retry. The selected execution projection omits the observer series; its original hash and selected controls remain explicit.

## Exact sequence and checks

The executed [reader](sources/reader.py), SHA256 97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b, opened only the existing generated cube. It checked the complete before mesh and required exactly one volume (3,1) with a nonempty shell. createGeometry([(3,1)]) changed only the discrete-volume geometry flag: all four tagged arrays, all native quality/signed-volume arrays, complete entity classifications and periodic metadata were unchanged. No surface parametrization or generation call occurred.

It then attempted exactly one mesh.optimize(method='Netgen', force=True), one rebuildElementCache(False) and one mesh write. Its counters record attempts; the controller's matching counts are explicitly declarations rather than independent operation telemetry. Generate and solve counts remained zero. The log and source/worker associations are reviewed; host-dependent native log bytes are omitted with their original hash.

The full after audit checked every actual cell, finite positive Jacobian/native/independent volume, exact source boundary coordinate bytes (including signed zero), exact oriented boundary faces, opposite internal tetrahedral faces, no orphan nodes, cube volume 343 mm³ and actual SICN ≥ 0.1. Boundary nodes retained their classifications below dimension 3, while interior nodes classified at dimension 3. There were no curve/surface periodic mappings. Interior node and tetrahedron recreation, retagging and count changes were allowed. Counts and tag changes do not establish node ancestry or a physical topology-change history.

The output MSH was reopened. All four tagged arrays, every saved quality array and complete classifications/periodic metadata were bit-identical to the after state. Its file hash was unchanged during reopen. [arrays.json](reports/arrays.json) includes four complete stages: before, after_geometry_flag, after and saved_reopen.

The independent [stopped-result peer](reviews/result-peer.json), SHA256 cc1e1c3b830d0a735161045b755fc0eaa01036a20b09731f9cad8a28e3c83b0c, checked all eight original output files, current input hashes and saved array/report joins using stdlib only. On every tiny JSON tetrahedron in all four stages it independently recomputed exact binary64-to-rational determinants: every signed volume is positive and each exact sum is 343. It also checked the twelve oriented boundary triangles, internal parity, one cell-adjacency component and zero orphans. Native metric array hashes and complete reported statistics reproduce from JSON. **Native SICN itself was not independently recalculated.** The reviewer did not parse the MSH or rerun Gmsh. These checks do not supply a separate global intersection, PDE or physical certificate.

## Inspectable generated meshes

| File | Bytes | SHA256 |
| --- | ---: | --- |
| [cube-before.msh](geometry/cube-before.msh) | 9,790 | e773cc4a2f68187c623e984eb9f58441f3fa5eed2733295e7eb26bd7b3910ac1 |
| [cube-after.msh](geometry/cube-after.msh) | 2,886 | 0db89b0cf7b4e57af1c6a091d999a7f521cd365f052f699a1798f05ba75eb92d |

Both are **generated toy cube data**, with fixed corners of the 7 × 7 × 7 mm cube. Neither is a scan, head mesh, part fitment reference or manufacturing file.

## Preserved history, guards and primary references

Preparation001 was blocked during source review before its tests or native run: inspect_live read global gmsh, but main imported it locally. The [blocked reader](lineage/reader001-blocked.py), [blocked peer](reviews/source001-blocked-peer.json), held projection and global-binding [diff](lineage/reader001-to002.diff) preserve that finding. Corrected002 added only global gmsh before the import; its fixture test also checks actual AST import/global visibility. No native failure is attributed to blocked001.

Root ran the corrected seven fixture guards and thirteen lifecycle mocks once: all **20** passed. Exact [fixture guards](sources/test_fixture_guards.py), [runner mocks](sources/test_runner_guards.py), [root review](tests/root20-review.json) and both logs are included. They use stdlib/AST/fakes and perform no scientific or head query. The exact [runner](sources/run_readback.py), SHA256 f7165620ac95b9095969b21ae912e87d491019e295a62155abbf33c2eb3b2944, preserves owned-process stop/wait, nonraising SIGTERM handling, handler restoration, remaining-budget timer and synchronous elapsed refusal. Transform records document exact source reuse. Historical HELD/null/false/unrun fields remain point-in-time records, followed separately by completed root guards and this native result.

The authored [exact-version study](research/Netgen-4.15.2-NOTE.md) and [source inventory](research/Netgen-4.15.2-sources.json) reference the official [Gmsh 4.15.2 source archive](https://gmsh.info/src/gmsh-4.15.2-source.tgz), SHA256 be3f66f225d27ba9fa014f07e83169285da8a051b0e8ab7103d88066b39bdd3e. They distinguish the Gmsh-specific Netgen optimizer path from generation and explain dynamic interior recreation and the volume-only flag. Archive-source matching to the installed binary build is not attested. The separate [capability002 projection](research/Netgen-capability002-projection.json) records the actual compiled Netgen token under pinned runtime hashes; it performed no meshing and granted no head authority. No upstream archive, library, binary or header body is redistributed.

The [existing cap-refinement capsule](../atomic-cavity-plane-clip-cap-refinement/) remains separate evidence. Neither it nor this toy cube establishes that a full-head Netgen trial will succeed. No live or future head outcome is included.

## Selected closure, rights and limits

[original-records.json](original-records.json) distinguishes exact copies, explicit selected-field projections and authored files; it inventories all eight original cube outputs and every selected original/public digest. All selected contract pin entries and digest values are preserved. Host runtime keys/values use role codes. Native argv, absolute host paths, observer series and private log bodies are omitted or represented by hashes. Projections cannot serve as execution contracts. This is a selected review closure, not the full private dependency/run closure or a standalone runnable workspace.

Run the unchanged verifier with python3 -B verify.py. It checks sealed bytes and selected-file closure only, without geometry or scientific execution. A seal or passing software fixture is not head mesh convergence, thermal resolution, strength/fatigue, a material/process choice, calibrated LPBF, OEM accuracy, PDE validation, fitment, professional engineering approval or manufacturing authorization. The 414 stronger Mesh_2 shape failures remain outside this cube's scope and unadmitted in the head study.

Original project code, authored records and generated toy data remain under the [project proprietary licence](LICENSE.project). Third-party software retains its own rights. No proprietary manual, supplier data, personal/vehicle data, raw scan or cylinder-head geometry is included.
