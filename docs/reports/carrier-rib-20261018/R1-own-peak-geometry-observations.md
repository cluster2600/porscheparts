# Native R1 geometry at its actual global stress peak

The observation queries R1 BREP `240109ca…` at the common global peak of its two closed coarse mechanical cases: element 83728 / integration point 1, (83.39717404347466, −15.380328571289892, 13.889129384939432) mm. Its four corner probes come from the same actual R1 mesh. The prior d64 reference observations remain separate. No native face ID or local measurement transfers from them.

This is a local geometric observation. It does not establish a global minimum thickness, singularity, converged stress or strength admission. Every native face and edge distance, all nearest-support ties, every normal-line hit and all unresolved qualifiers remain in the full assessment.

| Probe | First sorted native face | Distance (mm) | Qualified local chord to face (mm) | Support status |
| --- | ---: | ---: | --- | --- |
| case_IP | 60 | 0.0072030213624754676 | 0.085913083774408178 to 62 | native_D2_at_reported_UV |
| corner_0 | 60 | 7.2113962051093684e-13 | unresolved | closest_support_not_face_interior |
| corner_1 | 62 | 0 | unresolved | closest_support_not_face_interior |
| corner_2 | 11 | 6.3890100773500277e-13 | unresolved | unresolved_native_multiple_closest_supports |
| corner_3 | 60 | 4.3800795900274466e-14 | 2.8751619591984032 to 149 | native_D2_at_reported_UV |

“First sorted” preserves the original distance/index ordering and does not claim uniqueness at a boundary. The actual IP has a qualified 0.08591308377440818 mm normal chord from fresh B-spline face 60 to planar face 62, and a 0.06745367212333821 mm chord from the reciprocal nearest support. Its fresh nearest edge 263 joins these two faces, with native C0 continuity and a reported outward-normal angle of 137.05572865696482°. These remain local observations; the angle alone does not assign a material-side classification.

All qualified nearest-support chords are listed below; no support is filtered out:

| Probe | Native face → target | Chord (mm) |
| --- | --- | ---: |
| case_IP | 60 → 62 | 0.085913083774408178 |
| case_IP | 62 → 60 | 0.067453672123338207 |
| case_IP | 68 → 149 | 2.1887321277361664 |
| case_IP | 149 → 68 | 2.1887151948082537 |
| corner_0 | 68 → 149 | 2.1885865308108974 |
| corner_0 | 149 → 68 | 2.1885714378059191 |
| corner_2 | 68 → 149 | 2.1876373537839573 |
| corner_2 | 149 → 68 | 2.1876283207700911 |
| corner_3 | 60 → 149 | 2.8751619591984032 |
| corner_3 | 149 → 60 | 2.3688103109181706 |

The complete record retains 10 qualified and 32 unresolved nearest-face rows. Actual native resolution is 0.0000446679483124578 mm; no tolerance changed. The exact X-plane section at 83.39717404347466 mm has 41 native edge type/length/domain records, with optional radii. These records do not provide a sampled drawable outline or complete curve coefficients. The next separately reviewed extraction must save the actual native section BREP and sampled curves before a section image is possible.

No new CAD operation, numerical solve, image or geometry modification occurs during this metadata summary. The owner job is closed; its independent ROOT closure remains pending at the time of this frozen summary.
