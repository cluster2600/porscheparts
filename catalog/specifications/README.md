# Register of documentary specifications

This register keeps the values published in documentary sources: general
dimensions, capacities, gear ratios, tightening torques and angles. It stays
separate from `catalog/measurements/`, which is reserved for instrumented
sessions with raw readings and uncertainties.

An OCR transcription is not a validated measurement. Records imported from
PorscheFanatics therefore keep the raw source string, page and unit, with the
state `ocr_transcription_unverified`. They can guide a documentary model, but
must not drive manufacturing geometry before being checked against the primary
source or a physical measurement.

Regenerate both snapshots from a PorscheFanatics checkout:

```bash
python3 scripts/import_porschefanatics_specs.py \
  --technical-data /path/data/993-manual/technical-data.json \
  --torques /path/data/993-manual/torque-specs.json
```

