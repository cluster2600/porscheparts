# Required information for both OBJ files and their assembly

This list structures the request prepared in Gmail. Address, email content,
draft and any future reply remain private. Preparing a draft is neither sending
nor a supplier order.

| Priority | Requested information | Contract to complete |
|---|---|---|
| 1 | Donor identity/variant, part references, actual pairing of both scans | `exact_donor_variant`, component identity |
| 1 | OBJ unit, meaning of 0.5/0.21 mm suffixes, two independent physical dimensions per scan, tool and uncertainty | `scans[].scale_to_mm`, calibration evidence |
| 1 | Installed photos, shared coordinates, acquisition transformations; misaligned rotor back and missing coverage | Frames, registration, coverage map |
| 2 | Bore/hub, seating face, key/spline or fastening and axial retention | `rotor-hub`, `hub-output` |
| 2 | Input/output axes, support/engine faces and holes, spacing, threads and stacks | `case-mounts`, `mounts-engine`, bearings |
| 2 | Included/removed parts, original undecimated data, separate captures and applied repairs | Segmentation and acquisition provenance |
| 3 | Transmission type, teeth/ratio, rotation direction, seats, bearings, clearances/preloads, coupling location | `input-gearset`, `gearset-output`, bearings and coupling |
| 3 | Oil supply/return, threads, restrictions and seals | `lube-drive` and lubrication domain |
| 3 | Housing, guides and pulleys matching the donor; guide advertised 935/described 934 ambiguity | `rotor-inlet`, `inlet-guides`, `guides-engine`, belt |
| 4 | Documented masses/materials, three-shaft ratios, flow/pressure/torque maps, temperatures and test conditions | Mechanical, airflow and thermal models |
| 4 | Available catalogue/instructions and sharing rights; scan, derived CAD, simulation, printing and publication licence | Provenance and authorized uses |

For a dimension, identify the two measured features, unit, tool, uncertainty and
assembly state. An annotated photo of the same specimen with caliper readings
is initial documentary evidence; it does not replace metrology for critical
interfaces.

Reply processing retains “unknown” where information is unavailable. Another
rotor's diameter, commercial reproduction mass or a model-adjusted pose does
not validate supplied files.
