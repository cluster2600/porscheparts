# 935 drive: two candidate axial openings

The scan-derived drive surface has two visually round openings near the
provisional output axis. The [audit program](../../../twins/935-horizontal-cooling-system-f0/source/audit_drive_axial_openings.py)
fits their acquired sidewall arcs. These are **geometric candidates**, not a
verified bolt pattern, mating face, or historical mounting datum. The donor
identity and source-unit-to-millimetre scale remain unresolved.

The input is the pinned observed drive STL with SHA-256
`fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`.
The two visual seeds are (0, 30) and (0, −30) in the provisional assembly frame.
For each seed, the program keeps triangle centroids within 4.5 source units,
Z from −43 to −39, and absolute geometric normal Z below 0.7. It fits circles
with a robust radial loss and repeats the fit in the narrower Z interval
−41 to −39. A synthetic partial-circle fixture passes before scan analysis.

| Candidate | Acquired sidewall faces | Fitted centre XY, source units | Radius, source units | Radial RMS, source units | Angular coverage |
|---|---:|---:|---:|---:|---:|
| Positive Y | 534 | (0.938, 30.734) | 3.101 | 0.130 | 294.0° |
| Negative Y | 717 | (−0.486, −29.153) | 3.257 | 0.186 | 309.5° |

The two fitted centres are 59.904 source units apart in the provisional frame.
The narrower Z slices give radii 3.130 and 3.404 respectively. Those changes
show that the visible surfaces do not define a single nominal bore diameter
without resolving axial shape, scan error and feature identity. The arcs are
incomplete; these are fits to one scan, not independent dimensions.
Moving each visual seed by 0.5 source unit in X or Y changes the fitted centre
by at most 0.112 and 0.033 source unit for the positive and negative Y openings,
and the radius by at most 0.034 and 0.021 respectively. These are selection
sensitivity checks, not measurement uncertainty or manufacturing tolerances.

The [private inspection image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/drive-axial-openings-final.png)
shows the acquired faces and fitted arcs; its downloaded SHA-256 is
`585fa28863a2a0ddac7c4c39d71ee2c99b506f13ea6de8ad6d0c4631eac4180a`.
The [private numerical report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/drive-axial-openings-final.json)
was downloaded with SHA-256
`979921b62190d3112b68a5cd259c6221a9991833ce5ebd99bd71809d29788021`.
Neither the gallery of a related drive nor these scan openings establish their
mounting role, complete hole count, through condition, fasteners or tolerances.

## Boundary topology around the openings

The [boundary audit](../../../twins/935-horizontal-cooling-system-f0/source/audit_drive_opening_boundaries.py)
checks the same pinned STL without treating a projected circle as a hole.
It selects 120,429 triangles near the output axis (face-centroid radius below
50, Z between −58 and −34 source units), welds exactly matching STL vertices,
and counts edges with one incident triangle. An annular two-loop fixture passes.
The selected region has 3,373 boundary edges in 18 components and no edge
with more than two incident faces. Some components are caused by this regional
cut, so these counts do not describe the whole drive mesh.

Three simple boundary loops lie near the two visually selected openings,
away from the regional cut:

| Visual opening | Boundary edges | Observed Z span, source units | Interpretation |
|---|---:|---:|---|
| Positive Y | 266 | −51.52 to −38.98 | One loop folds through the axial depth |
| Negative Y, upper | 134 | −44.90 to −40.37 | Separate upper loop |
| Negative Y, lower | 133 | −52.90 to −45.47 | Separate lower loop |

The [private topological view](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/drive-opening-boundaries-final.png)
shows both XY and YZ projections; its downloaded SHA-256 is
`708d64267458881a82a9161cc494357550d1e401b83c33a883e7265e06e2952b`.
The [private report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/drive-opening-boundaries-final.json)
includes summaries of all 18 regional components and was read back with
SHA-256 `a09221bd31ea927b34440b45ccddcdc5d4e41f0e7a1c02c4ce136e1559c75070`.
The different loop structures show that the scan does not provide two matching
complete cylindrical bores. A boundary loop can delimit missing scan surface
as well as a physical opening; this audit does not establish a through-hole or
bolt pattern.

Reproduce on a private copy of the observed drive STL:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_axial_openings.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/axial-openings
```

Reproduce the separate topological check with a new private output directory:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_opening_boundaries.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/opening-boundaries
```

The output remains private. The next mechanical step is to inspect the
opposite side and axial sections of both openings, identify every attachment
feature around the flange, then obtain independent same-part scale and mating
face measurements. No functional PicoGK support is generated from these
candidate coordinates.

## Axial section continuation, 28 October 2026

The [depth audit](../../../twins/935-horizontal-cooling-system-f0/source/audit_drive_axial_depth.py)
reuses the hash-pinned observed drive STL and the original partial-circle
fixture. It fits three **non-overlapping** five-source-unit Z bands around each
visual seed and plots XZ/YZ sections of acquired face centroids. The image was
inspected; the local sidewall patches vary with depth. Red points in the plot
show fitted circle spans, not nominal diameters or designed walls.

| Visual seed Y | Z band, source units | Sidewall faces | Fitted radius, source units | Angular coverage |
|---:|---:|---:|---:|---:|
| +30 | −54 to −49 | 327 | 3.100 | 230.0° |
| +30 | −49 to −44 | 391 | 3.396 | 115.0° |
| +30 | −44 to −39 | 559 | 3.099 | 293.8° |
| −30 | −54 to −49 | 545 | 3.202 | 310.3° |
| −30 | −49 to −44 | 287 | 3.201 | 197.3° |
| −30 | −44 to −39 | 802 | 3.244 | 309.3° |

The maximum separation between the three fitted centres is 0.334 source unit
at the positive-Y seed and 0.280 at the negative-Y seed. The middle positive-Y
fit sees only 115° and has a larger radius than its adjacent bands. This is a
warning about incomplete surface coverage and fit stability, not evidence of
a machined taper or a specified coaxiality. The section plot also shows
disconnected acquired patches near the faces. It cannot distinguish missing
scan surface from a real internal opening. It does not prove a through-hole,
mounting role, fastener pattern, fit or manufacturing dimension.

Run with a new private output directory:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_axial_depth.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/axial-depth
```

The [private final report and section image](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-axial-depth-final-20261028.tar.zst)
have archive SHA-256 `8f453ef77ffdc295637b4b75a39ad24568646cb615819a25bcaee276ff1eed26`,
matching the GitHub asset digest. The report and image SHA-256 values are
`272c69600f959bf6d6c51c8f28bd174f990ad09b0877574ac35a6647384b4049`
and `ff951851cd293634f675ecf4cb438dbe1838f612b0d90d60f11bc89212e78627`.
An earlier overlapping-band exploratory archive remains private but is not the
accepted depth result. The next mechanical acquisition must resolve the actual
flange and opposite-side surfaces with a same-part dimension and mounted view.
