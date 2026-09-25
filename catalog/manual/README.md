# Quantitative register of the 993 manual

`993-workshop-manual-measurements.json` collects the quantitative values found
in the Porsche 993 workshop manual:

- the `technical_data` records already structured by Porsche Fanatics;
- the `torque_spec` entries from the torque tables;
- occurrences of dimensions, clearances, limits, pressures, masses, angles and
  thread sizes found in the OCR'd procedures.

The register currently holds 2,496 records: 111 technical data entries, 195
torques and 2,190 quantitative occurrences drawn from the 1,481 pages.
Occurrences can repeat when the same value appears in one procedure or in
several variants; each always carries the page and the short context needed to
go back to the source.

Pages 15, 19, 98, 108, 121, 137, 152–157, 177, 258 and 725–728 were checked
visually in the local PDF; the rest is kept as OCR occurrences to be verified
when they are used.

Each row carries the PDF page. The structured tables are derived facts, and the
OCR occurrences carry `ocr_unreviewed`: they must be checked visually in the
authorized copy before being used for CAD or manufacturing. The register is not
a copy of the PDF and contains no image and no full procedure text.

Regenerate from the Porsche Fanatics project data:

```bash
python3 scripts/extract_manual_measurements.py \
  --raw "/path/to/porschefanatic.com/data/raw/993-manual/layout.txt" \
  --technical-data "/path/to/porschefanatic.com/data/993-manual/technical-data.json" \
  --torque-specs "/path/to/porschefanatic.com/data/993-manual/torque-specs.json" \
  --output catalog/manual/993-workshop-manual-measurements.json
```

The provenance source is `SRC-PORSCHE-WORKSHOP-MANUAL-993`. The manual values
are not direct measurements by this project: they serve as manufacturer
references and as criteria for a future metrology campaign.
