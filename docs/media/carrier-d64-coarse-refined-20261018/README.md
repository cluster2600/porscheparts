# d64 coarse and refined mechanical fields

The [PNG](carrier-d64-coarse-refined.png), [SVG](carrier-d64-coarse-refined.svg) and [PDF](carrier-d64-coarse-refined.pdf) compare four actual cases on the same **d64a7faf** BREP. Columns show rigid/coarse, rigid/refined, K1000/coarse and K1000/refined. Rows show von Mises stress and actual displacement ×1, using a common camera, mm axes and field scales. Every boundary facet and all integration-point rows participate; orange markers retain every global stress maximum.

| Case | Coarse peak (MPa) | Refined peak (MPa) | Coarse / refined maximum displacement (mm) |
| --- | ---: | ---: | ---: |
| Rigid | 600.659493 | 925.772793 | 2.709626 / 2.710864 |
| K1000 | 1548.151984 | 2740.902001 | 16.478757 / 16.482678 |

The refined peaks share element 85784 / integration point 2 at (83.421659, −15.366811, 13.685695) mm. Their increase shows mesh sensitivity; it does not establish converged stress, adequate strength or an allowable. The original generated-volume refusal remains unchanged. A distinct exact same-serialized-operator and whole-H/2 diagnostic precedes these refined cases. These d64 fields do not establish the separate R1 candidate's mechanical response.

The [ROOT render review](root-render-review.json), [complete render receipt](render-receipt.json), [PNG/PDF visual review](local-visual-review.json) and [actual PDF raster QA](pdf-qa.json) close display revision 003. Earlier numerical renders remain preserved with their callout-layout refusals. The [numerical checkpoint](../../reports/carrier-rib-20261018/README.md#actual-mechanical-cases-on-the-saved-refinement) links the original mechanical, energy and refinement evidence.

`render.py` and its [source delta](source-changes.json) are exact copies, including their original workspace paths. They have not been rebased or replayed here. [external-references.json](external-references.json) explicitly lists all original field/mesh/deck/source hashes and the complete absolute plotting-runtime map. Full fields, meshes, decks, runtimes and earlier sources stay external. No self-contained or portable renderer replay is claimed. No new render, PDF, CAD, mesh or solve occurred during this copy. [provenance.json](provenance.json) records every exact source copy; [archive.json](archive.json) hashes every other file in this folder.
