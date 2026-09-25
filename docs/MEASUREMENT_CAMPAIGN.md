# Measurement campaign — phase 2

## State

The three polymer pilots are prepared, but no physical measurement session is
recorded in `catalog/measurements/` yet. The register now contains a separate
record of documentary specifications from the Porsche manual, which does not
replace an instrumented campaign. The repository has no access to a 993, to a
removed part or to an instrument: this document is therefore a handover dossier
for an outside contributor. It contains no invented dimension.

## Work order

| Priority | Part | Minimal method | Expected deliverable |
|---:|---|---|---|
| 1 | `993-INT-SWITCH-BLANK-0001` | Caliper and radius gauge | Seven dimensions D01–D07, three repeats, photo of the reference marks, JSON record |
| 2 | `993-INT-SEAT-RAIL-COVER-0001` | Caliper, depth gauge | Dimensions D01–D05 on both sides, check of the symmetry assumption, JSON record |
| 3 | `993-INT-DOOR-PULL-0001` | Caliper and scaled photogrammetry | Five interface dimensions, photos with a scale bar, manifest and JSON record |
| 4 | `993-INT-DASHBOARD-TRIM-0001` | Reading of the option code, then scaled photogrammetry and caliper | Evidence that no passenger airbag is fitted, fourteen dimensions in place **and** removed, three weighings, mesh and manifest |

The detailed plans are in the `parts/<part_id>/evidence/` directory. Priority 1
is the best first trial: the part is non-critical and its master geometry
already exists in `parts/993-int-switch-blank-0001/source/switch_blank.py`.

Priority 4 is of a different nature from the first three: it is a 1.4 m
freeform surface, and above all the only one whose measurement starts with an
**entry gate that can stop everything**. The dashboard trim can be measured only
on a vehicle without a passenger airbag; on an M562 car it carries the
deployment flap, and is therefore an occupant-restraint part. The plan has the
contributor read the option label before taking out an instrument.

## Contributor prerequisites

- Identify the vehicle's variant, model year and equipment without recording a
  chassis number, a license plate or any personal data.
- Photograph the part and its surroundings before removal, then identify the
  surfaces and axes with the same reference marks as in the measurement record.
- Declare the model, resolution, interface and calibration state of each
  instrument.
- Use at least three readings per critical dimension. A value typed in by hand
  stays `manual_entry`; it must never be presented as an instrumented stream.
- Keep raw images and point clouds out of the repository when they contain a
  vehicle identifier or data whose rights are not established. Submit only
  authorized, anonymized evidence.

## Session procedure

1. Copy `catalog/templates/measurement-record.json` to
   `catalog/measurements/MEAS-<PART>-<DATE>.json` and fill in the subject before
   any reading.
2. Check the zero and the instrument on a gauge block, a pin gauge or a known
   reference; record the actual status, not an assumed one.
3. Define the origin, the axes and the reference planes. The reference marks
   must stay identifiable in the photos and in the CAD.
4. Measure the interfaces before the decorative surfaces. Repeat each dimension
   without trying to make the values converge artificially.
5. Photograph the fasteners, clearances, bearing surfaces and contradictions.
   For the door pull, place a certified scale bar in every shot.
6. Enter the raw readings, compute the value from their samples, then record
   the uncertainty and its basis (`repeatability`, `instrument_resolution` or
   `combined`).
7. Run `make check`. If a measurement does not pass the validator, correct the
   transcription or the method; do not adjust the value to make the check pass.

## Decision gate

A part record stays `concept` until the session is complete and reviewed.
Moving to `dimensionally_reviewed` requires the critical dimensions, the
evidence files, the variant and a CAD review. Fitting a prototype is a separate
step: the clearances, photos and deviations will then have to be recorded before
any `prototype_fitted` status.

The three pilots are trim parts, but the door pull takes repeated manual loads.
No material, setting or geometry may be called safe or durable on the sole basis
of a good static fit.

## Optional CT brief

CT is not needed for the switch blank. It may be considered for the door pull if
the hidden interfaces are not accessible after removal, or for a polymer part
with internal channels. The records `SRC-HACHTEL-BASIC-CT-SCAN`,
`SRC-BMB-GERMANY-CT-RE` and `SRC-VISION-METRIC-CT-DIGITIZATION` are service
leads, not existing 993 measurements.

Any request must require:

- variant and part number;
- covered volume, resolution/voxel size and stated uncertainty;
- reference marks, scale, orientation and handling of hidden surfaces;
- raw volume or delivered format, segmentation, mesh and optional STEP;
- comparison between at least three interface dimensions and the manual
  measurement;
- rights to use and redistribute the delivered files;
- a prohibition on concluding the accuracy of a safety part from the scan alone.

A CT order or a part purchase requires separate approval by the maintainer. No
external spending or acquisition is presumed by this repository.
