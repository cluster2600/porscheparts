# Conditional scan scale consistency check

`check_scan_calibration.py` helps compare two independently measured dimensions of the same rotor or drive scan when they become available. No 935 measurement is supplied by this document. The input is private JSON: keep measurements, source points, scan and results out of public Git where they reveal private geometry.

The following values describe a **synthetic fixture only** and must not be applied to the 935:

```json
{
  "scan_id": "rotor",
  "scan_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "dimensions": [
    {"feature": "fixture length", "provenance": "synthetic fixture",
     "source_length": 100, "source_uncertainty": 0.1,
     "measured_mm": 200, "measured_uncertainty_mm": 0.2,
     "direction": [1, 0, 0]},
    {"feature": "fixture width", "provenance": "synthetic fixture",
     "source_length": 50, "source_uncertainty": 0.1,
     "measured_mm": 100, "measured_uncertainty_mm": 0.2,
     "direction": [0, 1, 0]}
  ]
}
```

`source_length` and `source_uncertainty` share the scan's original unknown coordinate unit; `measured_mm` and its uncertainty use millimetres. Each direction is a nonzero vector in that scan's frame along the measured feature. The dimensions must refer to distinct, nonparallel features of the **same identified specimen**; the program checks labels and numerical directions, not their actual physical independence. The uncertainties are nonnegative absolute bounds, not scanner marketing precision or standard deviations. Provenance should identify the source, feature, datum and measurement method without committing private information.

Run with a new output path:

```sh
python3 twins/935-horizontal-cooling-system-f0/source/check_scan_calibration.py \
  work/private-measurements/rotor.json work/private-measurements/rotor-check.json
python3 -m unittest discover -s tests -p test_935_scan_calibration.py -v
```

For each dimension, the scale interval is `(measured_mm ± measured_uncertainty_mm) / (source_length ± source_uncertainty)`, using the conservative endpoint combinations. Overlap is necessary for consistency within those supplied bounds, not proof of calibration. The forward and inverse matrices scale about the source origin using the **first nominal dimension**, even when intervals do not overlap; they are explicit conditional transforms and do not align or assemble the scans. The user-supplied hash is recorded but not checked against scan bytes by this tool. Registration, scan distortion, provenance, hidden geometry and physical fit need separate evidence. `scale_verified`, `physical_registration_verified` and `manufacturing_authorized` always remain false.
