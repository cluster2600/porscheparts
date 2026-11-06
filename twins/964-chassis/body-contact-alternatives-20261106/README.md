# Native B-width correction and alternative body contacts

Date: 6 November 2026. Direct re-reading of the supplied native Mi3 image
qualifies **612 mm as the combined opposed B bolt-head span**, giving a
source-only half-width of 306 mm under the printed equal-width convention.
The previous B-width-null reading was incomplete. This is a documentary
correction, not a new donor measurement or registration admission.

## Native source before source-family comparison

Two readers independently traced both transverse arrowheads/extension lines
to the opposed fore-foot bolt marks at B station and followed the lower mark's
B leader. The original embedded image was extracted directly from the pinned
`Mi/Coupe/Mi3.pdf`, image object 13, at 2120 × 1632 pixels. It distinguishes
these endpoints from D/E and the ball-joint-star references. Other/CH values
and scan geometry were not used to establish the reading.

The [correction record](mi-b-width-correction.json) extends the frozen
[owner source data](../owner-frame-data-20261105/source-data.json) without
editing its pinned bytes or the historical correspondence contract. Source
uncertainty and acceptance tolerances remain unknown. The sheet explicitly
applies to the 1992 Carrera 2/4 Coupe and Turbo Coupe; donor applicability is
not established by the matching model name.

Mi source point **B** is a separate namespace from the withdrawn scan-view
label `FrontObservedSurfaceB`, original face 537229. The correction reinstates
neither that cover-fixing witness nor face 574508 as a body contact.

## Source-only B/H alternative

[derive_nominal_bh.py](derive_nominal_bh.py) reads the hash-admitted original
Mi table and the independently reviewed B extension. It consumes no donor
arrays and derives the [nominal pattern](nominal-bh.json) in one Mi family,
with bolt-head and parts-removed states kept separate:

| Source contact | X, rearward from F | Mathematical side placeholders | Z above printed datum |
|---|---:|---:|---:|
| B bolt heads | -652 | ±306 | 167 |
| H bolt heads | 1274 | ±218 | 151 |

These are interpreted millimetres in the source frame. Signs do not assign
donor physical sides or handedness. The source quartet is non-collinear and
coplanar (rank 2), with plane `8x + 963z = 155605`. Correctly identified
non-collinear contacts can determine a numerical proper rigid pose; the quartet
does not independently validate off-plane geometry. At least one separately
observed off-plane named contact and a further unused body-contact/distance
check remain required before admission, together with justified units,
uncertainty, source applicability and contact construction.

The independently recomputed six pair distances agree. Source-only A/I/J
off-plane distances are calculator results, not observed holdouts or physical
accuracy. No tolerance, scan scale, fit residual or body interface is supplied
by those arithmetic identities.

Reproduce the source calculation with a fresh output path:

```sh
python3 twins/964-chassis/body-contact-alternatives-20261106/derive_nominal_bh.py \
  --output work/964-nominal-bh-replay-new/network.json
```

## Actual attachment evidence remains necessary

B's source role is the fore outer vertical body-fastening head of the fixed
longitudinal suspension support, distinct from moving-arm pivots, rack clamps,
cover fixings and the support's rear mounting hardware. The official
[Porsche PET](https://files.porsche.com/f/332100/b26b3c7233/kat013-d-911-94-katalog.pdf)
401-00 and an [original used-support photograph](https://kfz-kauert.de/?a=11268&lang=eng)
provide attachment/topology context. The seller listing and image filename
disagree on the suffix; no exact specimen/donor part match or reuse licence
is established. A teardown author's first-hand text supplies additional
assembly distinctions; unavailable linked photos were not treated as viewed.

The [review receipt](review.json) records current scan visibility and independent
checks. Mi A/J require the named lower bumper-mount heads with body/support
seating context; their flange interpretation remains conditional until that
assembly is observed. I requires the rear motor-mount flange-bolt head,
not the central engine-carrier stud/nut. Existing full and cropped views have
not identified those exact contacts. That is not proof of absence from every
original triangle. Nominal coordinates alone do not justify a targeted head fit.

The [progress ledger](progress-ledger.json) preserves the complete
[cell, mould, structural/manufacturing and native Omniverse goal](../contact-registration-20261106/goal-ledger.json).
No donor transform, functional cell geometry, material/process qualification or
native final-twin validation follows from this source correction.

The current engineering gate is blocked by qualified input data: actual labelled
body-contact/holdout measurements with calibration and uncertainty, and traceable
inner tunnel/upper-cell/hidden attachment surfaces. The ledger records the same
unresolved prerequisite across the three preceding goal increments. A current
narrow TetraVision sender/date check, including Spam/Trash, found no incoming
message; the approved enquiry remains pending. Autorobot remains an unsent draft.
