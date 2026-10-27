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

Reproduce on a private copy of the observed drive STL:

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 \
  --with scipy==1.14.1 --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/audit_drive_axial_openings.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/NEW/axial-openings
```

The output remains private. The next mechanical step is to inspect the
opposite side and axial sections of both openings, identify every attachment
feature around the flange, then obtain independent same-part scale and mating
face measurements. No functional PicoGK support is generated from these
candidate coordinates.
