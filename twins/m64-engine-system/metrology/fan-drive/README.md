# Fan-drive scan metrology (wave-2)

First full metrology pass on `SCAN-FAN-DRIVE-0P21MM` (study M64-ACQ-0005).

Artifacts in this directory:

- `fan_drive_metrology.py` — analysis script (mesh load, axis fitting,
  slab OD extraction, blade/tooth harmonic analysis). Run:
  `python3 fan_drive_metrology.py [--src PATH] [--out PATH]`.
- `fan-drive-dimensions.json` — raw machine-readable extraction (bbox,
  components, dimensions, harmonic analysis, verdicts).
- `metrology-report.json` — final report: scale hypothesis assessment,
  `scale_verdict`, verdicts, and `next_steps` acquisition asks.
- `findings.md` — narrative: what this pass proves, what it contradicts vs
  the wave-1 intake note and the BOM cooling lines, next acquisition asks.

Status: blade count, gear tooth count, and scale are all **UNKNOWN** at
F1_envelope; see `findings.md` for the exact evidence limits.
