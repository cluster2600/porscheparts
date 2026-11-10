# Correcting the monocoque dimensional baseline

The owner challenged the F2 floor curvature and the failure to apply the
original dimensions already supplied. The diagnosis is a modelling-process
error: F2 generated free profiles inside a nominal vehicle envelope without
binding them to the original body-control network. Its CAD and transport
checks did not establish fidelity to that network.

F2 is withdrawn as the current reconstruction baseline. Its dated source,
images and numerical receipts remain unchanged as a diagnostic study. The
unbuilt F3 proposal with arbitrary Z = 0 / −65 mm planes and a 65 mm floor
depth has been set aside privately. It is not a corrected donor model.

## Data that were already available

| Documentary register | Recorded observations | Scope |
|---|---:|---|
| [Owner frame data](../../../catalog/measurements/MEAS-OWNER-964-FRAME-20261105.json) | 57 | 37 coordinate/state rows and 20 opening spans; source frames and contact definitions remain distinct. |
| [964 body control](../../../catalog/measurements/MEAS-MANUAL-964-BODY-CONTROL.json) | 50 | Repair-control dimensions and point identities. |
| [964 interface spans](../../../catalog/measurements/MEAS-MANUAL-964-INTERFACE-SPANS-20261030.json) | 19 | 18 interface identities, including explicitly separate observations/variants. |
| [964 suspension alignment](../../../catalog/measurements/MEAS-MANUAL-964-SUSPENSION-ALIGNMENT.json) | 51 | Contact definitions, conditional ride-height settings and alignment data. |
| [964 interior reference](../../../catalog/measurements/MEAS-FIA-964-INTERIOR-20261105.json) | 7 | Six scalar interior dimensions and one printed sum. |
| [Separate 993 floor reference](../../../catalog/measurements/MEAS-MANUAL-993-FLOOR-CONTROL-20261104.json) | 25 | Related-model documentary observations, kept generation-specific; not substituted for 964 dimensions. |

The five 964 registers contain 184 observations. The separate 993 register adds
25, giving the audit's 209 catalogue observations. Its 210th row is the legacy
scan-height hypothesis, not another original dimension. This six-register
inventory is not an exhaustive inventory of every available Porsche source or
a contract requiring every row to become a geometric distance.

These are observation counts, not 209 independent surface coordinates.
Original source values, units, assembly states and datum definitions must be
retained. A fixture contact, a body-side attachment, a tyre-ground height and
a floor skin must not be silently substituted for one another.

## Executed source binding and shape checks

The [executed binding audit](report.json) and [traceability table](traceability.csv)
retain source values and definitions, the Mi B amendment and the unimplemented
model comparisons. F2 has **zero implemented comparisons to these observations**.
All 210 model values and dimensional differences are explicitly unknown. A null
difference is not a zero-error result.

[audit.py](audit.py) computes the missing-binding verdict. It does not approve
CAD, serve as a universal generator gate or independently qualify a contact
identity supplied by a caller. Its bounded scalar controls compare actual
point distances: a 100 mm fixture agrees with 100 ± 1 mm, while 110 mm fails.
The F2 regression checks the absence of implemented features/comparisons, not
an unconditional "unqualified" flag.

The [analytic source-shape witness](baseline-deviation.json), produced by
[baseline_deviation.py](baseline_deviation.py), confirms a 4.06849 mm sill dip
between level −65 mm landmarks and a 45 mm floor-control height spread at
X = 600 mm. The rear control rises to Z = 335 mm. These are F2-internal
departures in its own frame, not errors measured against the Porsche body.

The [whole-surface audit](surface-planarity.json), produced by
[audit_surface_planarity.py](audit_surface_planarity.py), also rejects all five
examined F2 regions: both floor bays, both sill undersides and the tunnel
underside. It checks 108 bicubic patches through their exact Bernstein control
nets. Coplanar boundary landmarks do not establish coplanar interior geometry.
The reported control-pole distances bound departure from a constructed reference
plane; they are not measured surface errors, best-fit residuals or Porsche
tolerances. Synthetic flat and tilted planes pass; a bowed interior with level
boundary poles fails. Planarity and horizontal attitude are checked separately.

## Editable source reference

The [reference manifest](reference/source-reference.json) and
[executed CPU readback](reference/runtime-receipt.json) record 37 original
coordinate/state rows expanded into 70 documentary datum points. The Mi B
bolt-head width amendment is applied only to that contact state. Two incomplete
rows remain X/Z projections; their unknown Y is not invented.

- [CH with mounted parts](reference/CH_parts_on.usda)
- [CH with parts removed](reference/CH_parts_removed.usda)
- [Mi source frame](reference/Mi_source.usda)
- [Provisional scan-frame plane outlines](reference/Scan_provisional.usda)

[build_reference.py](reference/build_reference.py) consumes the original
records and amendment directly. The four editable ASCII USD files remain in
separate frames. Plus/minus pair markers do not assign physical left/right
handedness. Point values, source IDs and metadata were reopened and checked;
the official USD checker reports no errors on these reference files. The scan
viewport wire uses float coordinates and separately retains exact double
construction corners. There is no filled floor skin, physical part or admitted
transformation between frames.

## Correction requirements

1. Consume the existing original records before generating replacement geometry.
2. Map each required dimension to an identified geometric feature and its source.
3. Establish the coordinate relationship before reporting a source/model delta.
   An unimplemented feature or unregistered frame produces an explicit unknown,
   never a fabricated zero error.
4. Check whole floor and underside surfaces. Level endpoint curves alone do
   not establish a planar surface between them.
5. Re-audit observed floor candidates in the original scan with fixed source
   triangle membership and reported residuals. A vertex-height histogram is
   not a plane fit or proof of an original cabin-floor datum.
6. Admit a new reconstruction baseline only after independent source-binding
   and geometric checks. Citing a measurement ID or matching the wheelbase
   cannot substitute for those checks.

The known original ground-to-body settings constrain named attachment contacts:
the Carrera 2/4 front outer crossmember bolt is 165 ± 10 mm and the rear
body-side arm attachment is 270 ± 5 mm, subject to the documented loading and
market variants. They do not establish a constant floor height. F2 implemented
neither those named features nor an admitted transformation to them, so no
physical dimensional delta is claimed here.

The existing scan frame uses tyres and symmetry. A reproducible matrix does
not itself establish registration to the body-control contacts. The corrected
work must preserve that distinction while using the data that are available.

## Re-audited observed floor candidates

The [executed scan audit](scan-floor-audit.json) retains the original triangle
identities, ribs and gaps. Fixed exterior-candidate crops were declared before
fitting. No height-based rejection, RANSAC, smoothing or horizontal plane was
used to obtain a favourable result.

| Fixed exterior crop | Original triangles | Area-weighted RMS to fitted plane | Maximum absolute distance |
|---|---:|---:|---:|
| Left | 72,207 | 2.347 mm | 5.935 mm |
| Right | 70,587 | 2.502 mm | 5.813 mm |
| Combined | 142,794 | 2.459 mm | 6.124 mm |

The combined plane is inclined by 1.499 degrees to the provisional tyre frame.
Flatness and level attitude are different properties. The residuals describe
the selected acquired exterior candidates; they are not a fitment tolerance,
a complete cabin floor, an interior skin or an original body datum. A broader
floor window retains larger departures and five local edge components, all
recorded rather than discarded.

The legacy Z = 271.7 mm estimate is reproduced as a 200-bin vertex-height mode,
271.69449 mm. It is not a plane fit. This execution re-hashed the retained
vertex/face arrays and edge archive. The original OBJ identity is inherited
from the earlier reviewed scan receipts, not a new OBJ hash operation in this
audit. Raw arrays, original triangle memberships and source images stay private.

## Source-to-scan correspondence

The [contact correspondence review](correspondence/README.md) separates each
documentary contact definition from its observed scan counterpart and metric
construction. Wider front and rear inspections retain the original triangles;
the front review also examines all ray depths and original mesh sections behind
the visible cover. Display cuts expose existing acquisition only.

The outer transmission-carrier fasteners support an anatomical H candidate
pair. Two frozen image-contour constructions hit shoulder surfaces, and a
single fixed connected-cap trial stops inside the cap instead of establishing
its complete physical rim. These constructions are rejected; they do not prove
that the acquired heads are unmeasurable. No qualified head-centre span or
source-to-scan transformation follows from them. Other named contacts retain
their scoped unresolved status in the ledger. No replacement CAD or structural
simulation is promoted on the strength of a contact name or a favourable
distance alone.

## Current status

This packet documents the source audit and blocks the unconstrained F2 shape
from being accepted as a reconstruction. A corrected complete monocoque has
not yet been generated. Original floor-surface coverage, datum correspondence,
functional interfaces and tolerances require explicit evidence before geometry
promotion. Road/track, manufacturing, structural and native Omniverse acceptance
remain open.
