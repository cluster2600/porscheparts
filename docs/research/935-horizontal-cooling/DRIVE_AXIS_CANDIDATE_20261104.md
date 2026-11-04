# Drive-axis surface candidate — 4 November 2026

The posed drive scan contains a partial, approximately cylindrical surface
near the provisional rotor axis. Its mechanical identity is unknown. The
[selection and fitting program](../../../twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/fit_drive_axis_candidate.py)
checks the private scan hash, selects face centroids in a fixed visual window,
and fits a cylinder using the existing within-scan angular-sector holdout.
It selected 9,566 faces, fitted a 6.915 source-unit radius and obtained a
held-out RMS of 0.120. The initial-frame angular coverage leaves a largest gap
of 175.1 degrees. The fitted axis is 0.833 degrees from the rotor-hub candidate
in the existing provisional pose. Scales and relative registration are not
verified; an angle or apparent concentricity cannot establish a functional
shaft, mating datum or engine fit. The same scan informed both fit and holdout.

A separate FreeCAD open partial cylindrical face covers 186.345 degrees in
the final fitted frame. It interpolates inside the crop, including missing
local data, and is not an acquired-surface mask, solid or complete shaft.
A 160-point same-scan-to-BRep screen and PicoGK import of the BRep tessellation
plus original selected triangles were completed. In an exploratory rigid
240-position rotor sweep, no crossings were sampled with the scan selection
or the fitted arc. The scan and fitted surface remain separated from the
rotor in this pose; this does not identify an adapter or validate clearance.
No hidden coupling was invented to close the gap.

The [scan selection and USD inspection package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-axis-candidate-20261104.tar.gz),
[open CAD and PicoGK package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-axis-arc-20261104.tar.gz),
and [rotor sweep and views](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-drive-axis-rotor-sweep-20261104.tar.gz)
remain private. Archive SHA-256 values are, respectively,
`868ff9d09281a11c34c9d14b675a65cfaf1163fb5be957c269c20d38c3cfd118`,
`466ba4911b934f64f949e691d0b6a5f4abe4c6921edaa05f6f878746e6c7f77c`, and
`89bc77fe4ab852d20315ed00eb1b7760056da9f7954a8d1d5131e572051fb382`.
Their files and GitHub release digests were checked. USD layers require the
previously preserved base scene and its layers.

Reproduce the selection in a fresh private directory after restoring the
pinned scan. The program rejects other scan hashes and rechecks the input after
fitting. Detailed geometry and per-face results remain in `work/`.

```sh
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 python twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/fit_drive_axis_candidate.py work/935-original-bound-assembly-20261028/native-002/drive_observed.stl work/935-editable-fragments-20261104/NEW-drive-axis
uv run --no-project --python 3.12 --with numpy==2.5.4 --with scipy==1.18.1 python -m unittest discover -s tests -p test_935_drive_axis_candidate.py -v
```

The unchanged scan, selection and fitted model were replayed exactly. The
selection fixture tests the radial and axial window, normal filter and
unpinned-input rejection. They do not validate the physical part. Calibration,
interfaces, internal transmission, structural and aerodynamic acceptance and
professional manufacturing review remain open.
