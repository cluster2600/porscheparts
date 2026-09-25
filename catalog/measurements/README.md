# Measurement register

A JSON record can hold either a physical measurement session or a quantitative
specification published by a reference document. A physical session contains
the subject, datums, instruments, raw readings and uncertainty. A documentary
specification contains its source, its page, its value text and its extraction
status; it does not replace an instrumented session.

The register does not replace the measurement plan
(`catalog/templates/measurement-plan.md`); it keeps the plan's result in a
machine-checkable form.

Among other things, the validator rejects a value that does not match its own
samples, an uncertainty finer than the instrument's resolution, a reading
attributed to an undeclared instrument, and an evidence level `A` without
repeats or known calibration state.

Create a record from `catalog/templates/measurement-record.json`, or fill it
directly from the instrument:

```bash
python3 scripts/capture_caliper.py --record catalog/measurements/meas-<part>.json \
    --dimension D01 --description "Eye bore" --port /dev/ttyUSB0 --repeats 3
```

A value typed by hand stays recorded as such: `manual_entry`, never
`instrument_stream`.

The documentary register drawn from the Porsche 993 manual is
[`MEAS-MANUAL-993-ALL.json`](MEAS-MANUAL-993-ALL.json). It carries 2,496 values
with page and provenance. The `ocr_unreviewed` values must be verified in the
authorized copy before they are used for CAD or manufacturing.

The physical campaign, ready to run, and its priority order are described in
[`docs/MEASUREMENT_CAMPAIGN.md`](../../docs/MEASUREMENT_CAMPAIGN.md). Until a
contributor has provided a part, a vehicle and the raw readings, the register
of physical sessions stays empty: zero verifiable instrumented measurements are
better than an invented dimension.

Regenerate the documentary record after an update of the manual register:

```bash
python3 scripts/import_manual_measurements.py
```
