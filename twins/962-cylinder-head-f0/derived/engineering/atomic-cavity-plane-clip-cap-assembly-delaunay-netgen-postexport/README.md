# Saved-head Netgen trial: quality rejection

**The volume remains rejected.** One bounded Netgen trial returned naturally with RC2 and no watchdog stop. Its complete native after audit found **210 positive tetrahedra with SICN < 0.1**, minimum **0.039074265058645995**. The unchanged acceptance gate requires every actual tetrahedron to reach **SICN ≥ 0.1**. Fewer poor cells and a higher minimum do not establish convergence or acceptance.

| Native full-mesh observation | Fresh saved input baseline | After Netgen |
| --- | ---: | ---: |
| Nodes / referenced nodes | 1,104,778 | 1,097,048 |
| Referenced interior nodes | 233,047 | 225,317 |
| Linear tetrahedra | 3,802,217 | 3,620,809 |
| Orphan nodes | 0 | 0 |
| SICN < 0.1 | 3,438 | 210 |
| Nonpositive SICN | 0 | 0 |
| Minimum SICN | 2.5872861583260695e−5 | 0.039074265058645995 |
| Fixed source surface nodes | 871,731 | 871,731 |
| Exact oriented exterior triangles | 1,743,878 | 1,743,878 |

The selected [worker projection](reports/worker-projection.json) preserves the original record hash **16f6ecc580d766c3c541517f0f89bd80d5cd0f660f40b157a04c5362c2245e6a**. The [controller receipt projection](reports/receipt-projection.json) preserves original hash **426e76e578b4ae0093e85515703f216c64cf1b2aaaf7474d6d8fb8a4641a32de**. The original worker retains status failed_outputs_preserved and stage reading_back_the_single_optimized_mesh: the quality refusal occurs after its saved-reopen checks. Its saved_mesh_identity_exact flag is true; no completed-geometric-volume status or acceptance flag is substituted.

## Completed sequence and its scope

The exact executed [wrapper](sources/mesh_delaunay_netgen_postexport.py), SHA256 **0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a**, reused the a326 owned controller. It opened the exact saved default-optimized MSH, SHA256 e32ef35be1171ec55477e921dd75def0066f9f1e21bd2821dfbe363270354522. Its sole baseline authority is the completed native worker **655156e6…['after']**, joined separately to the completed **7025fa94…** saved-file diagnosis. The older interrupted 1888 first-pass report is not used as an alias.

Before mutation, the unchanged audit_after routine freshly repeated all four tagged-array identities, complete counts, native metric arrays/distributions, signed volumes, source surface/classifications, tetra exterior incidence and opposite internal face checks. Its full observations matched that one worker.after proof. This fresh baseline incidence repeat is distinguished from the earlier diagnosis, which retained worker incidence rather than repeating it.

The wrapper observed the compiled Netgen capability token and exactly one volume (3,1) with a nonempty shell. It attempted createGeometry([(3,1)]) once, with no surface parametrization. A second complete audit confirmed that this volume-only flag changed no tagged arrays, classifications, native metric hashes/distributions, counts or incidence. Boundary identity also preserved every original source tag and binary64 coordinate bit, source-boundary entity classification and absent periodic mapping.

There was one Netgen(force=True) attempt followed by one rebuildElementCache(False). The recorded counters count attempts; they are not independent operation telemetry. Netgen and cache refresh returned. There was no generation, solve, fallback or automatic retry. The [tiny saved-cube route](../atomic-cavity-plane-clip-cap-assembly-netgen-cube/) and its exact 4.15.2 primary-source study are separate software evidence.

Interior node/tetrahedron recreation, retagging and count changes were deliberately allowed across Netgen. The wrapper instead preserved exact source boundary tags, coordinate bytes, entity classifications, oriented faces and periodic identity. It makes no old-to-new interior ancestry, matched-motion, physical topology-change or thermal-resolution inference.

## After and saved-file checks

All **3,620,809** actual cells received complete finite native metrics. After minima and nonpositive counts were:

| Quantity | Minimum | Nonpositive |
| --- | ---: | ---: |
| Native Jacobian | 3.295713806937255e−6 | 0 |
| Native volume (mm³) | 5.492856344895424e−7 | 0 |
| Independent signed volume (mm³) | 5.492856344895425e−7 | 0 |
| Native SICN | 0.039074265058645995 | 0 |

The native after audit saved the exact **1,743,878-triangle** tetra exterior, zero nonmanifold volume faces and opposite orientation on **6,369,679** internal faces. It saved zero orphans, all interior nodes at dimension3, unchanged source-boundary classifications and no curve/surface periodic mapping. Independent summed volume was **915453.1236217882 mm³**, relative error **1.1102230246251565e−16** against the source reference 915453.1236217883. The unchanged 1e−6 bound is numerical bookkeeping, not an OEM/manufacturing tolerance.

The single saved output was reopened. Its full four tagged-array hashes, classifications, periodic identity, boundary bits and MSH digest matched the optimized state. The final bound-input checks also passed. Positive Jacobians/volumes, exact boundary and saved identity do not override the failed SICN0.1 gate.

These scientific observations come from the completed native worker. The [independent stopped-result peer](reviews/result-peer.json), SHA256 **ccda5bedaba2cb743fda933b31ed88f2a3fa6881bbc3b50841c8d5f2eea77d6f**, verifies the exact JSON joins,12-file inventory, six source snapshots,126 small current pins and root maps for 128 inputs and three runtime identities bindings without independently parsing the MSH or replaying metrics/incidence. Root freshly hashed the whole MSH; this publication assembler inspected its metadata only. **The current 210 poor cells have no boundary/interior-location classification here.** The earlier counts of 1,435 and 2,003 or other poor-cell bins belong to earlier meshes and are not transferred.

## Lifecycle and immutable source lineage

Worker, controller and outer elapsed times were respectively **920.860677625**, **922.820792375** and **926.621943500 seconds**. These cover the complete trial, including input audits and output/reopen checks, not isolated Netgen timing. The native acceptance window was **1,200 seconds**, with sampled **8 GiB RSS**, sampled **1 GiB output** and two software threads. Maximum observed RSS was **6,753,583,104 bytes** over 1,794 saved observations. Sampling is not a certified peak or hard OS RAM/CPU/disk quota.

The [root closed projection](reports/root-closed-projection.json) retains the complete 12-file inventory, equality flags for all 128 input hashes after execution and three runtime hashes, and separate stopped controller/worker absence states. Private PIDs are omitted by explicit nested selectors. The root's earlier process exclusion matched exact comm names and was **not comprehensive argv-based sole-native exclusion**. A separate args observation of the owned parent/worker pair was recorded while running; that observation does not exclude every other native process. Its private body is omitted with its original digest. No stronger sole-native proof is claimed.

| Binding set | Count |
| --- | ---: |
| Fixed production-wrapper input map | 106 |
| Historical preparation001 input map | 112 |
| Selected test-corrected preparation002 map | 123 |
| Actual separately authorized child map | 128 |
| External runtime identities | 3 |
| Controller-owned executed source snapshots | 6 |

The [actual child projection](contracts/actual-projection.json) preserves original digest **b17c1eb1d304715c41bd2432334cb728f4741cd85d05595985954946b08f92e9** and external child-peer policy. The child peer remains a separate launch guard, avoiding self-reference. All held 112/123 and actual 128 selected input entries/digest values are retained.

The original six stdlib guards produced **four passes and two errors**, caused by a synthetic INPUT_HASHES map missing diagnosis.json. The production map of 106 entries already contained the actual diagnosis path. Frozen [root001 review](tests/root001-failure.json), [test-only delta](lineage/test-delta-002.json) and [diff](lineage/test001-to002.diff) preserve the cause; the host-dependent failure traceback log is omitted with SHA256074e6cabc98ce19a6a1459e59a48ed0c2feb834fe384feb7ec26e2f9ea14355c. Source 002 copied the wrapper and production delta byte-for-byte and added only that mock digest. The same six guards then [passed](tests/root002-pass.json). No source algorithm, acceptance threshold or budget changed.

The original [METHOD002](sources/METHOD-002.md) contains an overly broad negative-action sentence. Source/test files were read, hashed and AST-inspected by the preparer, but not imported or executed; the [independent002 review](reviews/source002-peer.json) explicitly clarifies this without rewriting the frozen document. All historical held/null/false/unrun metadata remain point-in-time records, with later source/test/child/result evidence separately associated.

## Selected closure, geometry and limits

The new MSH is **235,742,414 bytes**, SHA256 **4b983f4ab0134d01573059aecb8f4ba512dabbdfe54fbce6abaa0a06af29fe1d**. Its body is excluded. The unchanged source boundary is BIN9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4,871,731 vertices/1,743,878 oriented triangles. The existing [assembled-surface review ZIP](https://github.com/cluster2600/porscheparts/releases/download/untagged-3dc4679a17c16edf0fb4/962-bore95-plane0-assembled-unadmitted-review.zip), SHA2568ba6fc5dca47f3a51bc6298f481aaa334ac1096608552a96159a1d4688f6a4d5, is reused; no new geometry asset, BIN/MSH/ZIP, runtime/header body or raw scan is added.

The six actual source-snapshot hashes are fully inventoried. The new wrapper is copied exactly; five unchanged dependency bodies are linked to their existing identical public versions through original-records.json. [Original-records](original-records.json) distinguishes exact copies, selected-field projections, linked bodies and omissions, with original/public hashes. Private runtime locators use role keys; native argv, PID values, observer series and private log bodies are omitted explicitly. Projections are not execution contracts, and the selected capsule is not the full private run/dependency closure or a standalone runnable workspace.

The unchanged verifier (SHA256 prefix 3eff) checks only sealed bytes and selected-file closure: python3 -B verify.py. The [previous default optimizer/diagnosis](../atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport/) remains a distinct rejected result. Whole boundary identity preserves the 38 fixed cap cells as part of the source surface; no new semantic/OEM measurement is implied. The 0.0625 mm distance budget remains an analysis-mesh budget, not factory tolerance. All 414 stronger Mesh_2 shape failures remain unadmitted. There is no accepted/converged head volume, resolved thermal model, PDE/service prediction, strength/fatigue/creep proof, material/process qualification, calibrated LPBF, fitment, professional engineering approval or manufacturing authorization.

Project code and authored records retain the [project proprietary licence](LICENSE.project). Third-party software retains its own rights; upstream source archives, libraries and proprietary reference material are not redistributed.
