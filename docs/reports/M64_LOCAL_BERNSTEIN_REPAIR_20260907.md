# Local Bernstein repair on reference 935 — September 7, 2026

![Real CAD and before/after section of the local repair](../../twins/m64-cylinder-head/evidence/935-reference-bernstein-local-repair-before-after.png)

View produced from the two checked STEP files and their OCCT sections, with no
generative image. Source attributed to Wolfe Classics according to
`catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json`.
The `create-viz` skill guided keeping the views and scales and showing the
reference as a dotted line. The neutral render is not a temperature or stress
field.

## A new face and a solid were built

The candidate of bidegree **10 × 11** keeps the five boundary curves of the
source face in the checks performed. The face and then the closed solid pass
exact BRepCheck, including after STEP export and import. The tolerances of the
face and of its five edges stay at `1e-7`: no favorable reassessment by
increasing tolerances is used. The BOP self-intersection check then ended with
no defect reported.

The same local path measured by CAD intersection goes from **0.752667 to
1.602667 scan units**. Among the other paired rays, 39 remain unchanged to
within `1e-5`; two rays remain unresolved. This result is local and sampled,
not a thickness validation of the whole part.

The source remains the F53 reconstruction from a 935 research reference. It is
not validated M64 geometry, nor a certified scale, nor a part authorized for
manufacturing or for mounting on an engine. The global silhouette is not
replaced; **a local surface toward the air passage is actually modified**. An
unchanged bounding box does not mean that the whole outer skin is unchanged.

## Why reducing the degree helped

The [implicit-constraint field search](M64_IMPLICIT_BOUNDARY_BUBBLE_20260907.md)
had found a first 12 × 23 field. Its direct surface respects the curves, but
the OCCT contextual check of two edges fails near the ends: evaluation through
the adaptor gives a gap of about `1.668e-7`, while direct evaluation of the
surface at the same parameters gives `1.06e-13` and `7.29e-12`.

The control case using the unchanged source surface and the same wire assembly
passes. This is therefore not a simple wire reversal. The reimported 12 × 23
STEP becomes valid only after an automatic increase of two edge tolerances to
about `1.668e-7`: **this candidate remains rejected**. The diagnostic records
a divergence between evaluation paths; it does not claim to identify by
itself the faulty internal line of OCCT.

The new selection first minimizes the maximum degree, then the total degree,
and only then the amplitude on the initial grid. The numerical scores of the
14,641 fields were recomputed from the private coefficients already recorded:
the first report kept only the best field, not all the scores. No new
geometry fit is performed for this selection. 360 fields satisfy the amplitude
limit on the 81 × 81 grid.

| Exponents `(p,q,r,s)` | Bidegree | Maximum over 24,732 points | Minimum orientation ratio |
|---|---|---:|---:|
| **(4,2,2,5)** | **10 × 11** | **0.934757** | **0.968771** |
| (5,2,2,5) | 11 × 11 | 0.886633 | 0.966479 |
| (3,2,2,6) | 9 × 12 | 0.998871 | 0.979431 |

Only the first one is built. The last combination has very little margin under
the limit of 1. These maxima remain sampled, not certified global bounds.

## Construction and checks of the 10 × 11

`trial_transition_bernstein.py` multiplies the coefficients in a **Bernstein
basis**, with no high-degree monomial expansion and no BRepFill. The boundary
factor has a single nonzero coefficient before the product with `F²`, where
`F` is the equation of the analytic cylinder carrying the fifth trim. The
displacement is 0.85 at the target point. The poles of the bilinear source
surface are degree-elevated and then added to the displacement coefficients in
the chosen direction.

The knots take exactly the original UV domain; the same parametric curves and
intervals are attached to the edges. The operations are performed on a copy
of the master. The B-Spline construction conditions and the curve attachment
functions are described in the official references
[Geom_BSplineSurface](https://occt3d.com/dev/doc/refman/html/class_geom___b_spline_surface.html)
and [BRep_Builder](https://occt3d.com/dev/doc/refman/html/class_b_rep___builder.html).

| Native check | Result |
|---|---:|
| Error of the point displaced by 0.85 | `3.89e-14` unit |
| Maximum curve/surface error at the same parameters, 121 points/edge | `6.25e-9` unit |
| Same check on the source surface | `6.25e-9` unit |
| Maximum gap of first derivatives at the sampled boundaries | `9.61e-12` |
| Gap between factored formula and OCCT surface, 6,250 points | `7.14e-14` unit |
| Maximum native displacement on these points | `0.934182` unit |
| Minimum native orientation ratio | `0.968804` |
| Face before and after export/import | exact BRepCheck valid |
| Tolerance of face and five edges, before and after import | `1e-7`, unchanged |
| Sewing | One shell; zero free or multiple edges |
| Solid before and after export/import | exact BRepCheck valid, 20,431 subshapes checked |
| Topology | One solid, one shell, 4,929 faces; zero non-manifold edges |
| BOP self-intersections of the full solid | Completed, no defect reported |
| Change of the six bounding limits, before export | 0 |
| Volume change | `+10.6963` units³, i.e. `+0.0008584%` |
| Surface area change | `+7.49387` units² |
| Volume change due to the STEP round trip alone | `4.66e-10` unit³ |

The normalization coefficient is `89.8421`, versus about 497,655 for the
12 × 23. The better stability is not inferred from this ratio alone: it is
observed in the native evaluations and checks. The absolute maximum of the
Bernstein displacement coefficients is `3.18756`; this is not the maximum of
the surface.

An additional independent check compared **all** the tolerances of the two
full STEP files: 4,929 faces, 10,222 edges and 5,278 vertices. The
distributions are strictly identical, with minimum and maximum `1e-7` in each
category. The single 10 × 11 face and its five edges also keep this value
after sewing and importing the full solid.

The [independent global Bernstein bound](M64_BERNSTEIN_GLOBAL_BOUND_20260907.md)
establishes for the stored scalar polynomial `|D| ≤ 0.9512202009568349` over
**the whole UV square**, and not only at the grid points. It uses an exact
rational subdivision of the recorded floating-point coefficients. Its scope
does not include a global bound on OCCT evaluation rounding, nor a mechanical
or manufacturing validation.

## Private artifacts and limits

On Kali, under:

```text
/tmp/917-f50/out/m64-local-transition-bernstein-20260907-low-degree/
```

- `private-bernstein-coefficients.npz`: reusable private coefficients, parameters and poles.
- `private-replacement-face.step`: 10 × 11 face, SHA `168327ff82585039ccd4c62e4004a73b0176fca42f6ea09d49e8582f37ed33c5`.
- `diagnostic-candidate.step`: full solid, SHA `42057011e25ecc48b215a58e979a0d9bcf4769f2f96f9690b751a81a7bde2cd8`.
- `surface-report.json`, `solid-report.json`, `audit-report.json`: separate native steps.

SHA of the surface/solid/audit reports:

```text
33f99d631f77a6a6bc14a4a9a3dea531f2e40c2a44a31a97606e76a94209636f
6482f829ed18a836ed54351b630bb2703ab5c3d2b99063b428a1da83ef5784e9
d2bb2b1195b1ef320ca8dc9fac7a57a910aa9477a28c3022f771f4e70eb508af
```

Published image: SHA `18057ee6e124420960d5f1d8e742d8f000898f688e78ba68141107c973eaa08a`.
The [redacted public summary](../../twins/m64-cylinder-head/bernstein-local-repair-summary-20260907.json)
contains no coordinates, no private face/probe indices, and no STEP/NPZ.

Supporting reports, under `/tmp/917-f50/out/`:

- `m64-bernstein-adaptor-boundary-audit-20260907.json`, SHA `af85432b9e495205b5672e6eca49f2426e8c2a9a2e31c0e39e00fd9b2e685cec`: rejection of the 12 × 23 and automatic tolerance increase on import.
- `m64-low-degree-localized-fields-20260907.json`, SHA `645bfb542e396528e6372f449b71a27554976d45929ba98ff9c32807dc7526c8`: ranking of the three lowest-degree candidates.
- `m64-bernstein-complete-tolerance-audit-20260907.json`, SHA `c68b62f1386ff8879e3d6c90e52937cd2949252a73c1b7179a93e08e79cb85fe`: full private inventory of each tolerance, with exact histograms and a specific check of the modified face.

The BOP self-intersection check completed within its 300-second cap, with
`exit 0`. It is not replaced by the success of BRepCheck alone. The audit and
construction scripts are limited to two CPUs and 4 GiB; the numerical
selection is limited to 60 seconds. A first launch of the audit stopped before
computing on an old remote helper; after bringing the tested helper in line,
the audit resumes without rebuilding the CAD. The initial report is kept as
`audit-report-import-error.json`.

Two unit tests verify the Bernstein products and the construction of the
localized factor; four others cover the audit and the field search. Four tests
bind the redacted summary to its evidence, verify the ray counts and prevent
its promotion to a released M64 part. The CAD evidence above comes from the
native runs, not from these tests alone.

## Next avenue and result of the separate trial

**Update:** the [local C2 reinforcement on the thinnest isolated path](M64_ISOLATED_C2_REJECTION_20260907.md)
has since been built as a separate surface, then rejected at the slope filter
before any face or sewing. It is not combined with the 10 × 11 solid. The
earlier proposal and audit remain below.

`audit_remaining_transition_faces.py` inspected the four remaining weak
non-adjacent rays in the real source geometry. The four entry surfaces are
non-rational bilinear, with four isoparametric boundaries and a single wire.
They therefore do not need the cylindrical factor used in the previous repair.

- Two rays, `1.144959` and `1.304774` units, cross the same pair of faces in
  opposite directions. A correction must check these two paths together, not
  treat them as two independent defects.
- Another path is `1.427734` units.
- The weakest remaining one is `1.052418` units; its entry point is very close
  to a parametric boundary. Normalizing a global bubble at this point could
  over-displace other areas of the face.

The proposed avenue is a bubble on a **local UV support**, with cubic factors
giving zero displacement, first and second derivatives at the edge of the
support. A B-Spline representation with local knots, of degree 6 × 6, could
keep the initial curves and a C2 blend without a high global degree. These are
properties of the proposed construction, **not an already built surface**. Its
amplitude, its direction toward the air passage, the collisions, the coupled
rays and the continuous bound will have to be checked before and after any
construction.

Read-only report, private:
`/tmp/917-f50/out/m64-remaining-transition-feasibility-20260907.json`,
SHA `463eaa85b14c10c2e1284049fd57642fce8e93ad1b73e5b4a37da4e7c9768a75`.
No new CAD had been launched during this preliminary audit.

Thermal behavior, fatigue, turbo load, M64 interfaces, LPBF manufacturing and
physical checks are not validated by this repair. The other thin areas still
have to be treated. The F53 master keeps its SHA
`700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`.
