# Figure 33: the first-window stock mechanical checkpoint

These are the actual closed rigid and K1000 stress/displacement fields for stock BREP `42da92cc`, native mass **1.267835378 kg**, with the first main-window cut-profile inset changed from 1.5 mm to 2.8 mm. The inset is not a measured wall thickness. The image does not show the later `d64a7faf` rib trial.

| Stock support case | Global IP von Mises maximum (MPa) | All-node displacement maximum (mm) |
| --- | ---: | ---: |
| Rigid end eyes | 621.1414615781972 | 2.7715852188872883 |
| K1000 end eyes | 1633.1285701272036 | 18.025226400906668 |

Both complete global peak objects are retained, including their common single tie at element 39298 / integration point 1, at (26.77366323459092, 13.63043441388483, 29.778672530278612) mm. The independent energy checks pass their unchanged 10⁻⁴ limit. These are initial-mesh results; stress convergence, strength and fatigue acceptance remain open.

The four panels share the original orthographic camera, axes and colour scales. Every one of the 45,264 boundary corner facets is submitted in each panel, without decimation. Stress colour is the maximum of the adjacent T10's four integration-point values; the separate global marker retains the actual integration-point maximum. Displacement colour uses corner nodes, and drawn displacement is true scale ×1. All-node extrema retain midside nodes. The current mesh has 158,156 nodes and 84,903 T10 elements.

Both cases retain Fz = −4,000 N, My = 850,000 N·mm, E = 107,000 MPa and Poisson ratio 0.31. K1000 is a total 1,000 N/mm per eye and axis, distributed over that eye's actual nodes. No earlier model's load roster or stress field is substituted.

The [render review](proofs/render/root-terminal-review-001.json) binds the actual PNG, SVG and PDF, with actual PNG and rasterized-PDF visual checks. Layout 001's overlapping annotations remain a [historical visual refusal](proofs/history001/root-terminal-review-001.json); the accepted revision changes only their label offset. The [mechanical review](proofs/FEA/root-solver-terminal-review-001.json) binds both actual cases and their independent energy/peak checks. The [later rib-trial review](proofs/rib-trial/root-terminal-review-001.json) is separate: its mass is 1.274797998 kg and local geometry gates pass; fresh surface, protected interfaces, mesh and mechanical results remain pending in this snapshot.

The [inventory](archive.json) verifies stored bytes. Sources, complete render metadata and compact case proofs are included. Full NPZ/INP/DAT/FRD field/mesh/deck bodies, CAD and the 219-file plotting runtime remain [explicit external dependencies](external-dependencies.json). No new portable render replay, solver run, refinement, CAD construction or physical qualification is supplied by this image capsule. Original execution paths in copied controls remain historical absolute paths.

The [geometry comparison](../first-window-stock-comparison-20261018/README.md) and [139-file source delivery](../../design-20261016/first-window-stock-20261018/archive.json) retain the earlier stock construction. This image supplies a mechanical checkpoint for that same stock design, not an approved manufacturing release.
