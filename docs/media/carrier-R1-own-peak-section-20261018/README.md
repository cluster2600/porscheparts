# R1: actual peak section and projected normal chords

The [PNG](carrier-R1-own-peak-section.png), [SVG](carrier-R1-own-peak-section.svg) and [PDF](carrier-R1-own-peak-section.pdf) show the actual native section of the **240109ca** R1 BREP at **X = 83.39717404347466 mm**. The left panel retains the whole Y–Z outline; the right panel uses the actual peak-element Y/Z bounds as a display crop. Both receive all **41 native curves / 1,833 sampled positions**, with equal physical axis scale. The marker is R1's actual common coarse stress integration point.

| Retained observation | Actual value |
| --- | ---: |
| Peak (X, Y, Z), mm | (83.39717404347466, −15.380328571289892, 13.889129384939432) |
| Section drawing deflection | 0.001 mm |
| Largest section-plane residual | 4.263256414560601 × 10⁻¹⁴ mm |
| Face 60 → 62 normal chord, full 3D length | 0.08591308377440818 mm |
| Face 62 → 60 normal chord, full 3D length | 0.06745367212333821 mm |

Dashed chords are **Y–Z projections of retained 3D endpoints**. Their endpoint X coordinates generally differ from the section plane; their printed lengths are the full 3D lengths. They are not measurements of this section's thickness or of the part's global minimum wall thickness. The full [native observation](native-observation-assessment.json) and [summary](observations-summary.json) retain all ten qualified chords and 32 unresolved rows. No unresolved observation was converted into a thickness result.

The [raw native section](actual_common-section.brep), its [descriptor](actual_common-section.json) and [complete sampled outline](actual_common-section-data.json) are copied byte-for-byte. Raw curves were preserved before sampling; full sampled data were preserved before checks. [section-assessment.json](section-assessment.json) and the [ROOT section review](root-section-review.json) record the original sampling controls and actual checks. The native BREP is the geometric intersection; drawing samples are its retained display representation.

The [ROOT render review](root-render-review.json), [render receipt](render-receipt.json), [ROOT visual review](root-visual-review.json), [local visual review](local-visual-review.json) and [actual PDF raster QA](pdf-qa.json) close this actual figure. The [R1 checkpoint](../../reports/carrier-rib-20261018/README.md#actual-r1-peak-geometry-and-saved-refinement) links the separate mechanical and refinement results. This image grants no convergence, strength, fitment or manufacturing qualification.

The copied render.py, extract.py and source records retain their original work-tree paths. They have not been rebased or replayed here. [external-references.json](external-references.json) lists the original executable source locations, all input hashes, all 219 plotting-runtime files and actual loaded runtime hashes, plus the external native candidate and complete mechanical records. A self-contained or portable replay is not claimed. No new render, PDF, CAD, mesh or solve occurred during this copy. [provenance.json](provenance.json) records every exact source copy; [archive.json](archive.json) hashes every other file in this folder.
