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

## Angular holdout check

An additional check reserves four contiguous angular sectors in each Z band.
For each sector, the baseline and each candidate period are fitted only on
the other three sectors; the held-out prediction errors are then pooled.
The angular cut is placed inside the largest unobserved gap, because the
acquired arc crosses the conventional ±180° cut. Synthetic 22-lobe controls
pass both with and without this coordinate wrap. These sectors all come from
the **same incomplete scan**; they test fit stability, not independent
metrology or a complete circumference.

| Z band, source units | Best held-out period | Held-out error reduction | 22-lobe error reduction |
|---|---:|---:|---:|
| −20 to −15 | 7 | 16.95% | −4.99% |
| −15 to −10 | 17 | 6.16% | 4.34% |
| −10 to −5 | 17 | 7.90% | −3.51% |
| −5 to 0 | 8 | 8.57% | −0.99% |

The preferred periods still differ across bands, and some individual held-out
sectors get worse even under the best pooled result. The numerical evidence
therefore does not select a spline count. The [private holdout report](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/output-period-holdout-final.json)
was downloaded and checked against SHA-256
`7734f009d355bc1848d71fb1c9e5c22fec90239e0d17e30bf434029728af40d7`.

```sh
uv run --no-project --python 3.12 --with numpy==1.26.4 python \
  twins/935-horizontal-cooling-system-f0/source/picogk-hub-space/audit_output_patch_periods.py \
  work/935-assembly-0p7-20261025/six-run-001/drive_observed.stl \
  work/935-assembly-0p7-20261025/hub-output-metrology-001.json \
  work/NEW/output-period-audit.json
```

This command now includes the angular holdout check and writes its results in
the same private report. Use a new output path; earlier in-sample receipts are
retained separately.

The next coupling definition requires a full-circumference measurement of the
output feature, its axial shoulder and thread, the mating rotor/hub geometry,
and independent calibration. Until then, the PicoGK annulus remains an empty
visual occupancy envelope. No output spline profile, fit, fastener, safe speed
or manufacturing geometry is approved by this audit.
