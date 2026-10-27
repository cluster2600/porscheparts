# 935 drive-output surface feature audit

The public [Wolfe Classics Fan Drive gallery](https://www.wolfeclassics.com/shop/p/porsche-935-fan-drive-3d-scan)
visually shows a ribbed upper protrusion with a threadlike tip and a flange
with studs. This observation does not identify the corresponding triangles in
the owner's OBJ, prove the same donor, count splines, specify thread pitch, or
show how the rotor is retained. The gallery images are referenced, not copied
into this repository.

The previously reconstructed **22-lobe patch is on the input side**, about
357 uncalibrated source units from the provisional rotor axis. It cannot be
transferred to the output hub. To test the output separately, the
[audit program](../../../twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/audit_output_patch_periods.py)
reads the pinned observed drive STL and four-band metrology receipt. It selects
face centroids at radial positions 5.5–8.5 source units, with Z from −20 to 0.
In each five-unit band it fits a baseline linear in Z plus the first angular
harmonic, then adds one 6–40-lobe harmonic at a time. A synthetic 22-lobe
fixture passes before the scan is analyzed.

| Z band, source units | Faces | Highest in-sample period | Highest variance reduction | 22-lobe reduction |
|---|---:|---:|---:|---:|
| −20 to −15 | 1,586 | 8 | 20.68% | 2.29% |
| −15 to −10 | 1,484 | 11 | 17.06% | 2.59% |
| −10 to −5 | 1,319 | 8 | 16.96% | 1.56% |
| −5 to 0 | 879 | 8 | 14.13% | 0.84% |

These are **in-sample** scores on one incomplete scan. The preferred period
changes across bands, and around half of each circumference is missing.
Neither 8 nor 11 nor 22 is accepted as the output spline count. The result
does not rule out a ribbed or threaded feature outside the acquired patch.
The [private report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/output-period-audit-final.json)
was read back with SHA-256
`fbcc9b593e9b0b1e92782861d988b7190494ceab689aa5f36dd93b20b6b53a1b`.

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 python \
  twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/audit_output_patch_periods.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/935-assembly-0p7-20261025/hub-output-metrology-001.json \
  work/NEW/output-period-audit.json
```

The next coupling definition requires a full-circumference measurement of the
output feature, its axial shoulder and thread, the mating rotor/hub geometry,
and independent calibration. Until then, the PicoGK annulus remains an empty
visual occupancy envelope. No output spline profile, fit, fastener, safe speed
or manufacturing geometry is approved by this audit.
