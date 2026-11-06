# 935 inspection stages: explicit USD units

The scan scale is not calibrated. Some private inspection stages conditionally
convert source coordinates by `0.001`, assuming source units are millimetres.
That assumption is not evidence of physical size or assembly fit.

An audit of the recent inspection layer chain found root stages without authored
`metersPerUnit`. USD supplies a fallback of `0.01` metres per stage unit for
those stages even when a sublayer has authored `1.0`. Thus opening those layers
individually can interpret coordinates 100 times smaller than intended under
the conditional millimetre assumption. This does not establish which scan
scale is correct. Historical layers and their pinned evidence are unchanged.

A new private inspection overlay authors `metersPerUnit = 1.0` at its root and
retains the conditional `0.001` coordinate conversion. Its private release
archive is `935-assembly-profile-witness.tar.gz`; the stage is not a released
part or a physical validation. Rebuild and reopen a new root stage rather than
changing an immutable historical layer. Do not treat this metadata correction
as calibration of either scan.

Before using a new 935 SI inspection stage, run:

```sh
python twins/935-horizontal-cooling-system-f0/source/fragment-frames-20261104/assembly-placement/check_usd_units.py path/to/stage.usdc
```

The guard requires authored root-stage metadata equal to one metre per unit;
it deliberately reports `source_scale_verified: False`. It cannot check the
coordinate conversion, scan scale, assembly placement or physical suitability.
The targeted regression checks the missing-root and wrong-unit cases using
synthetic USD layers, and verifies acceptance of explicit SI units. The actual
new overlay passed; the previous short-shaft stage failed for missing root
metadata. `usd-core` is required to execute the guard and its regression.
