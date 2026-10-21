# Current 127-poor-cell head checkpoint

The single apex 1613790 replacement completed its procedural audits and reduced the observed positive cells below SICN 0.1 from **129 to 127**. The whole-head quality gate remains **rejected**. The minimum SICN is unchanged at **0.039074265058645995**, and the stronger Mesh_2 criterion, with 414 historical surface-face failures, remains open. No physical, material, manufacturing, fitment or head-strength qualification is claimed.

The [saved head report](results/head-application.json), [independent stopped review](reviews/head-result-peer.json) and [root acceptance](reviews/head-root-acceptance.json) distinguish procedural completion from quality rejection. Complete after/reopen audits report 1,097,222 nodes, 3,621,771 TET4 cells and 225,491 referenced interior nodes, with no nonpositive metric reported. These are frozen worker observations joined by root and saved-data reviewers; they are not a second head decode or a global overlap certificate.

## Review mesh

The exact generated research mesh is available as [head-volume.msh.gz](downloads/head-volume.msh.gz), **78,888,772 bytes**, SHA256 `0fbb26a76d9a78edc9b71a5bbe075b355a25fe752476b9d242e91ff294308775`. Root's [delivery receipt](downloads/head-volume.msh.receipt.json) records complete lossless decompression to the original 235,786,462-byte MSH, SHA256 `8b16732d63cc69e48af113f6b618cc6378aaf121dbe1c63920dd6dd5eab8d07a`, unchanged original bytes and a negative private-path marker scan. The selector freshly hashed the completed gzip; it did not decompress or inspect head geometry. The separate [independent gzip byte review](reviews/head-download-byte-peer.json) confirms full decompression and every-byte equality without a geometry decode. This is a generated research mesh, not an OEM scan or a manufacturing release. Availability of the file grants no reuse rights; the [project license](LICENSE.project) remains view-only.

## Evidence sequence

- The complete original star has 28 cells and a fixed 16-node, 28-face shell. All 28 necessary face bounds pass their declared strict threshold; a necessary bound alone establishes no feasible repair.
- [Generation](results/generation.json) produced a 16-node, 24-cell cavity with two positive poor cells and was rejected. Its [full arrays](data/generation-arrays.json), source and stopped evidence remain preserved.
- One [saved-cavity Netgen trial](results/Netgen.json) produced 20 nodes and 44 cells with four interior nodes. All 44 local cells pass SICN 0.1; the minimum is 0.27182687371445746. [Complete candidate arrays](data/Netgen-arrays.json) remain inspectable.
- The [exact local-domain record](results/local-domain.json) retains all 1,324 pair verdicts and 74,144 plane-triple metadata associations for the original 28 and candidate 44 cells. Its scope is relative local occupied-region equality, not global head embedding or physical validity.
- The [read-only current-parent context](results/current129-context.json) binds all 28 shell-face owners: 16 exterior and 12 internal. The [application source](sources/head-application/reader.py) reuses the original apex storage tag, adds three nodes and 16 element slots, preserves outside/source metadata and retained original parameters, and performs one write plus full reopen audit.

The earlier census launch-command deviation `d60fff29…` and `declared_controller_command_conformant: false` remain historical evidence; this checkpoint does not rewrite that event. Rejected generation, the saved Netgen review's first metadata-representation refusal and correction, source guard/history records, original false or null preparation fields and controller declarations are retained. The head remains quality-rejected. Native cleanup is attributed to the frozen controller's finally/wait and saved receipt; root directly observed its controller, not a native-worker PID or universal descendant absence.

## Provenance and inspection limits

[Original records](original-records.json) and the existing [byte verifier](verify.py) account for exact bodies, explicitly declared private-path projections, complete inventories and identical source-snapshot aliases. No numeric, tag, floating-point word, bool/null or list-order field is removed or normalized. Any bulk archive uses the existing deterministic byte helpers and a complete member ledger. The verifier checks selected byte closure, not engineering correctness.

Predecessor bodies and runtimes are linked through the prior [current129 checkpoint](../current129-thermoelastic-setup/README.md), [combined current204 application](../current204-combined-application/README.md), [earlier single-apex application](../apex1474426-head-application/README.md) and their exact ledgers. They are not duplicated or silently upgraded to current evidence. The capsule is selected review evidence, not a standalone native runtime. Original 210-poor cells and the stronger Mesh_2 criterion’s 414 historical surface-face failures remain distinct from the new 127-poor result.

Root owns all native runs and publication. Separate source and stopped peers have bounded scopes. The selector authored earlier head/checker lineage; assembling this evidence adds no independent mathematical or physical qualification. No native, geometric or scientific replay is part of publication.
