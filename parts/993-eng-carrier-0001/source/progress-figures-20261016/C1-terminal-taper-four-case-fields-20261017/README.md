# Figure 28 — coarse and raw-refined terminal-taper fields

Four closed linear-static CalculiX results use the same native terminal-taper BREP. The coarse mesh has 89,536 C3D10 elements; the raw refined mesh has 91,040. Each panel displays every boundary corner triangle: 47,344 for a coarse panel and 47,552 for a refined panel. All eight panels share axes, camera and colour scales. Displacement is shown at its true scale (×1); insets crop only the display.

| Mount model | Coarse global VM (MPa) | Raw-refined global VM (MPa) | Coarse Umax (mm) | Raw-refined Umax (mm) |
| --- | ---: | ---: | ---: | ---: |
| Rigid | 697.3125042834432 | 1218.0720144829165 | 2.7940146926593012 | 2.794387779638359 |
| K1000 | 1977.809950603409 | 3716.0389795903557 | 18.17020118428633 | 18.172701245623323 |

K1000 is a total 1000 N/mm per eye and per axis distributed over the actual retained end-node sets. Both mesh variants retain identical complete load/support contracts: E=107000 MPa, ν=0.31, Fz=−4000 N and My=+850000 N·mm. Every global integration-point tie and displacement maximum remains recorded. The four original energy audits pass at their unchanged 1e−4 tolerance.

The raw refinement retains its original strict volume refusal. The taper retains its original post-Build law refusal and strict STEP exchange refusal. These results do not qualify H2, demonstrate stress convergence, supply a strength allowable or qualify the physical part. The larger stress peaks and near-stable displacement are actual diagnostic results.

The PNG, SVG and PDF are exact closed-render outputs. ROOT checked the complete receipt and viewed the PNG: all eight panels, four insets and English table were legible without observed clipping. The PDF received metadata/font checks, not a raster visual review. Historical renderer, whole plan, data summary, source delta, tests, logs and ROOT review are preserved byte-for-byte.

Full coarse fields/decks belong to the [coarse delivery capsule](../../design-20261016/native-C1-terminal-taper-20261017/README.md); full refined fields and refusal proofs belong to the [dependent raw-refined capsule](../../design-20261016/native-C1-terminal-taper-raw-refined-20261017/ACTUAL_REPRODUCTION.md). This small archive duplicates neither. `dependency-required-members.json` binds all 48 original numerical records consumed by the plot; `workspace-aliases.json` binds eight additional small source/metadata paths. The 219-file plotting runtime is identified, not redistributed. [REPRODUCTION.md](REPRODUCTION.md) separates stored verification, report analysis and the historical plot command. No portable rerender is claimed.

The numerical dependency's stored-byte verifier is closed under ROOT `eb9ea03d043e067120748fd8fbcfa6e41e56bf45f47879610bb42a8b30aa3c6c`; its single analysis replay is closed under ROOT `de1cdbf76e8b810bf674da691a5bd618238b42b3cbab14491f1dc89bc23c377a`. All 696 inherited/new input streams and all four complete refined energy/peak reports were verified; the report objects and serialized bytes match their originals. This numerical replay did not rerender Figure 28 or change any original refusal.

The actual durable numerical dependency retains complete inventory `34ded330d73f559499f7379ecfbfcb707a27721dde73648275f2079ee288a6d5`. Its one exclusive byte copy preserved all 100 source files plus the generated self-excluding inventory. No numerical analysis was repeated during that copy.

The [independent ROOT durable-copy review](dependency-proofs/root-fine-copy-terminal-review-001.json) is closed RC0: it verified all 100 source and 101 destination file identities and byte hashes, preserving the original 13-file capsule. Its [owner terminal](dependency-proofs/fine-copy-terminal-collection-001.json) is retained alongside that review.
