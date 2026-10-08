# Interface survey — 964 first, then a 993 check

Status as of 2026-10-08: **measurement preparation, not a released design**.
The [CSV sheet](derived/interface-measurements-20261008.csv) keeps the 18
identities of the manual's register. Nine carry a documentary transverse span
from that register, and P13 and P14 a span from plate 50-05a; ten have a
projectable XY hypothesis. **No anchor XYZ is validated.**
P8, P9 and P10 are not in this register; no point is invented to fill the
numbering. This register is not the complete inventory of a body shell.

Relative X along the chain (`x_relative_status` in the sheet):

| status | points | meaning |
|---|---|---|
| `DETERMINE` | P20, P3, P5, P17, P12, P18, P19, P21 | placed from published dimensions (datum chain closed from plate 50-05a) |
| `MESURE_DESSIN` | P13, P14, P15 | scaled off plate 50-05a, +/- 8.6 mm |
| `MANQUANT` | P6 | no published longitudinal dimension |
| no data in the contract | P1, P2, P4, P7, P11, P16 | listed, not located |

No point is `INVALIDE` anymore: P21 is placed by the rear diagonals O and N
read unbracketed (`source/datum_chain_50_05a.py`; see the [README](README.md#the-rear-of-the-chain)).

## Reading the views without making them say more than the scan

`source/interface_review.py` reuses the existing contract and the registered
vertices. It produces a local 3D view and a plan view, a report that binds its
inputs, its code and the CSV sheet by SHA-256, and the sheet itself:

- blue: relative X **determined** from published dimensions (P20, P3, P5, P17,
  P12, P18, P19, P21); not a measured XYZ;
- green: relative X scaled off plate 50-05a, +/- 8.6 mm (P13, P14);
- vertical dotted lines: Z unknown, with no tolerance range or anchor volume;
- graphic plane under the scan: only there to separate the hypotheses from the
  observed skin. Its height must never enter the CAD;
- not projected, but kept in the sheet: P6 (no X), P15 (X scaled off the plate,
  no published span) and P1, P2, P4, P7, P11, P16 (no data in the contract).

The CSV sheet is regenerated from the contract and the ledger alone and holds no
scan geometry; `tests/test_964_interface_review.py` checks it byte for byte.
**The scan-based review (views and report from `main()`) is pending a rerun**
on the machine that holds the registered vertices `verts_vehicle.npy` of
[scan-recalage-20260925.json](derived/scan-recalage-20260925.json). The review
of 2026-09-25 described a contract that never reached main and was removed.

A point visually close to a skin does not prove it is the right mounting.
No nearest neighbor fills in Z automatically. The tie of the chain to the scan,
`REGISTRATION_X` (P17 at -465.7 mm in the vehicle frame), carries
+/- 7.6 mm and is **not validated**. P12 designates the gearbox crossmember
support, never the rear suspension. The span P5 to P12 (1535.6 mm) does not
define the wheelbase. The manual's tolerances apply to the pair spans, not to
each symmetric Y; `y_half` assumes symmetry.

The images contain scan data: they stay out of Git until redistribution rights
are confirmed. The CSV sheet is a state of knowledge, not a form to fill in by
overwriting earlier values.

## Proposed survey order

| Priority | Zone / identities | Survey to obtain | What it unlocks |
|---|---|---|---|
| 0 | Vehicle and acquisition | 964 C2/C4, model year, factory or modified wide body, gearbox, suspension modifications; unit, instrument, stated accuracy, scan processing, assembled/disassembled state | Applicability of the scan; no automatic transfer to the 993 |
| 1 | Structural frame; P17/P18/P19 | Physically identify the L/R reference surfaces; XYZ and uncertainties; independent checks of the spans and of distances R/S | Registration on the body shell instead of a ground plane derived from the tires |
| 2 | Front P3/P4/P5/P6 | Mount centers and axes, seating planes, center distances, diameters and bracket geometry; survey P6 without giving it an X by symmetry | Front axle and suspension strut interfaces |
| 2 | Rear P13/P14, engine P15/P21, gearbox P12 | Identification by photos and markers; XYZ, axes, seating faces, hole patterns, limits of neighboring parts | Real rear interfaces; physical check of the published X of P12/P21 and of the drawing-scaled X of P13/P14/P15 |
| 3 | Tunnel and shift linkage, per variant | Interior-side and underside scan with identified fairings; brackets, axes, joints, swept envelope over all gears, removal access | Shift routing and tunnel shape; not only its lower skin |
| 3 | C4 driveline | Tube/shaft, flanges and front differential: geometry, axis line, mounts, powertrain motion and access; documented states | C4 provision; no arbitrary diameter or clearance |
| 4 | Upper shell and openings | Bulkhead, wheel arches, pillars, roof, window openings, doors, hinges and locks; inner/outer surfaces and accessible thicknesses | A complete shell, not a floor pan with invented volumes |
| 4 | Other interfaces | Seats, belts, pedal box/steering, fuel tank, lines, harness, heating/ventilation, bumpers P1/P16 and other mounts P2/P7/P11/P20 | Restraint, services, assembly and maintenance to integrate into the model |

This table is a work list, not a procedure for disassembling or loading the
vehicle. The survey and its access must be prepared with a competent operator.
Dynamic configurations and required clearances must be defined with the
responsible engineer; no value is imposed here.

## Data expected for each new measurement

Keep a new record, without modifying the historical evidence:

- point identifier **and side**, function and annotated photo without personal or
  vehicle identifiers; definition of the measured feature (hole axis, seating
  plane, etc.);
- generation/variant, vehicle configuration and load state;
- XYZ, units, frame, transformation to the scan and justified uncertainty;
- useful axes, diameters, surfaces and center distances; both sides measured
  separately;
- instrument, metrological verification, date, operator and method kept in the
  private file; public data anonymized and authorized;
- native file, file digest, rights and check points independent of those used
  for registration.

The target accuracy and the acceptance criterion must be set **before**
acquisition, according to the interfaces. The 55.1 mm ground scatter, the
7.54 mm symmetry residual and the +/- 7.6 mm `REGISTRATION_X` tie are not
instrument uncertainties.

## Moving to interface CAD

The next version may place editable functional surfaces and axes once their
identity, their XYZ and their frame are supported, with verification against
independent checks and a metrology review. Unknowns stay unfilled (`null`, not
zero); one anchor found does not validate all the others. A 964 campaign
qualifies neither the 993 nor every C2/C4 variant.

Layup, inserts, allowable loads, molds and road/track validation remain later
steps. This review generates no manufacturing file.

## Reproduce

From the repository root, with the registration environment already
documented:

```sh
python twins/964-chassis/source/interface_review.py \
  --vertices /private/path/verts_vehicle.npy \
  --output /private/path/new-review
python3 -m unittest discover -s tests -p 'test_964_interface_review.py'
```

The output folder must be new; a vertex array different from the archived
registration is refused. The PNG files stay local. The `interface-measurements.csv`
written by the run must be identical to the published
[sheet](derived/interface-measurements-20261008.csv); the run's
`interface-review.json` is not published yet and holds no raw geometry.
