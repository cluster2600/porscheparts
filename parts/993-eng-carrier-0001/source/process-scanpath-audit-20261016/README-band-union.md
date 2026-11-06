# Containment in the intentional vertical band

On a real grid of the left region, the GEOS overlay of the band does not exactly
contain its own free domain D. The same rational witness rejects D and
the unchanged material R. The test keeps this rejection; no tolerance masks it.

`exact_band_union.py` checks R directly within the union of the same elementary
convex sets as `vertical_contact_band`, before their overlay. The IEEE
coordinates of the ±0.2 mm vertical sweeps remain identical. The cut at Z ≥ 0
is made on the exact fractions, without re-encoding the material.

The triangulation is not assumed correct: the exact sum of the chains of
positively oriented triangles must equal the complete boundary of the Polygon,
holes included. By winding numbers, these triangles then partition the
domain with no gap and no positive overlap. Each material triangle is
either contained in an attested convex set, or partitioned by the lines of the
candidate primitives with the existing exact helper. The closure of this finite
union also covers all boundaries.

The real case passes in 1.561 s: 102 material triangles, 95 primitives and
12 collective partitions. The polygons, their SHAs and the receipt are kept
in `band-union-evidence/`. The five tests also cover a genuine opening,
material outside the band, material below the plate and incomplete or
duplicated triangulations. The proof was independently reviewed.

This proof concerns the unchanged material within the **intentional union**;
it does not claim that the old GEOS Polygon contains it. It constitutes
neither an admission of the seven regions nor an audit of the exposed toolpaths.

The separate helper `exact_convex_union.py` speeds up the same decision by
successive rational convex subtractions. Each subtraction preserves the
area exactly; it partitions the half-plane outputs without double
counting. Positive remainders carry verified witnesses outside all the
primitives. Five tests, including the same unchanged real material and a gap of
positive area of the order of 10⁻³⁰, lock this independently reviewed variant.
The old helper and its receipts remain unchanged.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_exact_band_union.py -v
```
