# Zero-area faces and equality of the encoded surface

`exact_zero_face_coverage.py` does not clean a mesh. It checks whether a
face of **exactly zero** area adds no point to the XYZ surface already
covered by the non-zero triangles of the **same group**.

Its IEEE vertices are interpreted as rationals. The whole segment between
the extremes, or the point if all vertices coincide, is intersected with
the candidate triangles. The union of the closed intervals must cover
`[0,1]` entirely. Covered end points with an empty middle are refused;
another zero-area triangle cannot serve as covering material. Boxes serve
only as a preselection, without tolerance.

The [real droit012 witness](zero-face-coverage-result-001.json) proves the
coverage of the 44 zero-area faces identified: 18 in the grids and 26 in the
skins. The proof counts 290 rational intersections and keeps the identities
of the 25 groups concerned. Six targeted tests pass.

This would allow removing **only these covered faces** without changing
the set of points of the encoded XYZ surface. No removal was carried out
by this witness. The proof does not by itself preserve the intrinsic area of a
2D chart already collapsed during remapping; it admits neither topology, nor
contacts, nor paths. These checks remain mandatory afterwards.

```sh
AM_PYTHON -B -m unittest discover -s tests -p test_carrier_zero_face_coverage.py -v
```
