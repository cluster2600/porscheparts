# Fixed-plane clipping: preserved refusal, software fixtures and rejected head screen

This capsule preserves actual bounded results for the separately assumed
finishing datum z=0, retaining metal at z≥0. It does not establish an OEM
machining datum. Coordinates are millimetres. Earlier surfaces, fixed-mask
contracts, failed trials and numerical thresholds remain unchanged.

| Actual stage | Result |
| --- | --- |
| EPICK source001 `38b2e1e5…` | Compile succeeded. First cube returned 2 before export: “Nonfinite or below-plane coordinate”. The coordinate, condition and magnitude were unrecorded. Other three cases were unrun. |
| EPECK source002 `190432d4…` | Distinct compile succeeded. Four unchanged literals returned 0/0/0/3 and passed the frozen independent fixture assessor. |
| New head finishing-datum trial | Procedure returned 0; **surface-quality screen failed**: 3,112 faces below 2/29, minimum 3.582992623128027×10⁻⁵. No surface or volume admission. |

The exact cube has 13 vertices/22 faces, volume 1,755,904 mm³ and cap area
23,104 mm². The through-hole prism has 24/48, volume 12 mm³, cap area 12 mm²
and Euler 0. The 9/14 above-plane case is byte-identical to its input; the
empty case is a report-only refusal. The actual paired assessor checked every
coordinate/triangle/ID, retained above-plane geometry, closed links, exact
volume and complete cap/support coverage, including exact hole intersection
and positive-area overlap tests. Its native minimum and exact squared quality
metric remain separate. The peer record attributes its checks explicitly.

The head report records 869,355 vertices/1,739,126 faces, 3,508 newly
constructed on-plane points, 865,847 retained coordinate matches and 35,880
removed input coordinates. Native cap area is 8,678.423193507433 mm² and
volume 915,453.1229484563 mm³. The owned process stopped and was reaped and
removed after 35.495 s; all 78 input pins remained unchanged. Native closed
volume/self-intersection checks are source-bound procedural evidence.
Independent full head arrays, topology, cap/void/features and two-sided
distance checks are **not completed**. No HXT or head PDE was invoked.

EPECK performs exact construction, followed by an audited approximate binary64
embedding. Exact equality restores unchanged input Point bytes; only new exact
z=0 points are materialized and converted. Nearest rounding and exact final
embedding are not claimed. Point IDs are selected-input coordinate-bit rows
or UINT64_MAX, not original894/Porsche identity or construction history.
Old fixed-face masks cannot establish the new variant's distance; the unchanged
0.0625 mm representation and SICN 0.1 volume gates still apply.

`original-records.json` binds exact copies and complete retained phase input
and artifact maps. `projections.json` is an explicit allowlist, excluding raw
commands, machine paths and owner/container IDs; it is not full native records
or standalone runtime reproduction. No executable, upstream CGAL headers or
full head BIN/ID arrays are distributed. Small literal geometry is included in
962SURF1: 8-byte magic, LE uint64 vertex/face counts, binary64 xyz rows and
uint64 oriented triangle rows; ID files are LE uint64 rows.

Run `python3 -B verify.py` for sealed byte/scalar consistency only. Source
snapshots preserve the actual implementations; running them requires the
recorded compatible repository layout and separately obtained CGAL5.6 runtime.
The verifier does not rerun clipping, scientific queries or fixture assessments.
No head strength, thermal/material/process/LPBF calibration, physical validation
or manufacturing authorization follows from these software results.
