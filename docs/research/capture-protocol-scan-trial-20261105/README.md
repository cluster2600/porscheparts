# Scan-vs-reference trial on the 935 head scan, 2026-11-05

Issue #4 asked for the scan acceptance part of
[CAPTURE_PROTOCOL.md](../../CAPTURE_PROTOCOL.md) (section 7) to be run end to
end without physical capture. This trial runs it on the one licensed scan the
repository holds whose raw file is reachable from the working host, against
documented reference values, with thresholds committed before the run.

**Verdict.** The protocol runs end to end on an admitted scan and a documented
reference. Of the four pre-registered checks, one passes (C3, spark-plug bore),
one is not observable (C4, valve guides), and the two port checks C1 and C2
cannot be assigned: under one reading of which face is the intake, C1 passes and
C2 is not observable; under the other, C2 fails and C1 is not observable. No
result calibrates the scan, states its accuracy or measures the specimen.

## Upstream audit

Before any check, the inputs were audited, as [AGENTS.md](../../../AGENTS.md)
requires before consuming geometry.

| Input | Verdict |
|---|---|
| Scan | `SCAN-935-XTREME-CYLINDER-HEAD`, SHA-256 `4623d5d3…66486`, 104,598,077 bytes. The copy read was the owner's local download; its digest equals the registered one, and the script refuses any other digest. 1,281,608 vertices, 2,466,040 triangles, open (not watertight). |
| Licence | `open-reuse-user-confirmed`, redistribution of derivatives allowed ([scan record](../../../catalog/scans/scan-935-xtreme-cylinder-head.json)); the raw OBJ stays outside Git. |
| Unit | 1 OBJ unit = 1 mm, the owner's declaration ([935-scan-engineering](../935-scan-engineering-20261029.md)). Not physically calibrated. Nothing was rescaled. |
| Frame | `twins/reference-935-cylinder-head/source/scan_frame.py`: C normal to the combustion face, port faces at B = −251 and B = −62. Reused unchanged. |
| Reference | Xtreme catalogue ranges for four head families, transcribed in [935-faithful-replica](../935-faithful-replica-20261028/README.md). The specimen's family is unknown, so the union of the families is used. Manufacturer ranges, not specimen measurements. |
| Other 993 scans | None admissible here. `SRC-SKETCHFAB-993-GT2-RAW-SCAN` is CC BY 4.0 (re-read through the Sketchfab API on 2026-11-05) but its download needs an account (HTTP 401) and it has no scale; the 964 underside and the fan-drive scans have unknown licences; the 917 scan is not on this host. |

## Pre-registration

[`thresholds.json`](thresholds.json) was committed alone in `2e09eac7`, before
the measurement script existed. At that point only the scan's envelope, already
published, was known. Feature identification used views of the scan made after
that commit, as the contract allows and states.

| Check | Feature | Reference | `T` |
|---|---|---|---|
| C1 | intake port opening, equivalent diameter at the flange plane | 35.0–47.0 mm | 0.5 mm |
| C2 | exhaust port opening, same measurand | 35.0–41.5 mm | 0.5 mm |
| C3 | spark-plug bore, circle normal to its axis, ≥ 3 mm below its opening | 10.647–14.0 mm (M12×1.25 minor to M14×1.25 major) | 0.5 mm |
| C4 | valve-guide bore, circle normal to its axis | 8.0 mm | 0.5 mm |

No registration dimension exists for this specimen, so P5 step 3 (scale and
register on registration dimensions) could not be applied: the declared unit
stands in for it. That departure is recorded in the contract.

## Results

Produced by [`source/measure_trial.py`](source/measure_trial.py); every station
is in [`results.json`](results.json). Sections are chained by mesh-edge
identity ([`source/sections.py`](source/sections.py)), so no gap is bridged and
a loop counts as closed only if the scanned surface closes around it.

| Check | Value | Outcome |
|---|---|---|
| Port at the low-B face | 45.07 mm at 0.5 mm from the face (closed section); 45.0–45.1 mm to 4.5 mm deep, then a step to 39.9–40.0 mm | value for C1 or C2 |
| Port at the high-B face | no closed section in the first 20 mm; open arcs covering up to 97 % fit 41.2–41.5 mm | not observable |
| C1 / C2, if the low-B face is the intake | C1 45.07 mm in 35.0–47.0 | **C1 pass, C2 not observable** |
| C1 / C2, if the high-B face is the intake | C2 45.07 mm against 35.0–41.5 + 0.5 | **C2 fail, C1 not observable** |
| C3 | two bores either side of the port plane A ≈ 128, axes tilted 29.8° and 27.9° from C; eight closed normal sections between 3.0 and 5.5 mm below the opening (open stations are listed, not judged): 11.20–11.34 mm, circle RMS ≤ 0.10 mm | **pass** |
| C4 | two closed 7.0 mm sections at the head back; both continue 5 mm beyond it with the same diameter, so they are solid protrusions (studs or hardware), not bores | **not observable** |

What the numbers say, and no more:

- **C3** places both bores between the minor and the major diameter of an
  M12×1.25 thread (10.647–12.0 mm). That is consistent with the catalogue's
  "12 mm" plug option. It is not a thread identification: the scan does not
  resolve a 1.25 mm pitch, and the pitch is the repository's reading.
- **C1/C2** turn on an identification the geometry here does not settle. Both
  ports lie on the valve plane A ≈ 128; the scan shows no valve seat or guide
  that would tell intake (larger valve) from exhaust. The rule measured the
  45 mm mouth, which is a 4.5 mm deep counterbore, not the 40 mm port behind
  it; the rule is applied as committed and not changed after the fact.
- The combustion chamber section near the deck (89–92 mm) was seen during
  identification. It was not a pre-registered check and is not judged.

## What the trial changed in the protocol

The trial is the first execution of section 7. Its consequences are written
into [CAPTURE_PROTOCOL.md](../../CAPTURE_PROTOCOL.md) as rule changes, and the
status of each proposal P1–P7 now says whether it was exercised.

- P5 needs a **measurement station defined by features, not by the face**:
  "at the flange plane" landed on a counterbore. The next contract must name
  the station (for example "the narrowest closed section within 20 mm").
- P5 needs a **feature identification step committed before results**, with an
  explicit fallback: when the identification is not established, both
  assignments are judged and reported, as here.
- P5 step 3 has no registration dimension for most public or purchased scans;
  a declared unit is an admissible stand-in only if it is recorded as such.
- `not_observable` is a third outcome beside pass and fail. Two of four checks
  ended there: an open scan cannot show what it did not capture.

## Reproduce

```bash
~/.venvs/porscheparts-ci/bin/python -I \
  docs/research/capture-protocol-scan-trial-20261105/source/measure_trial.py \
  /path/to/935-xtreme-cylinder-head.obj results.json
```

About one minute on the WSL host. The script writes an array cache next to the
OBJ, never in the repository. No mesh, section or cache is committed.
