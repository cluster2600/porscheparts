# Body-contact context and original boundary incidence

Date: 6 November 2026. Status: **observed-source inspection, not registered
interfaces**. The previous [23-contour network screen](../contact-registration-20261106/README.md)
rejected that fixed subset; it did not establish absence of F/G from the scan.
This continuation examines a broader original context rather than relaxing
the size or fit thresholds.

## What the source actually identifies

Mi3 Fig 1 labels F/G as centres of 25 × 34 mm holes. It does not explicitly call
them jacking receptacles. F's open-circle mark is at the outboard front cabin
corner and is distinct from the nearby rectangular box/dot. G's open-circle
mark is at the outboard rear cabin corner, distinct from the larger oval drawn
in the adjacent rear rail/pod. Schematic symbol sizes do not provide metrology.
No explicit F/G-to-wheel-axis station dimension is supplied; the wheelbase and
separate strut/ball-joint references cannot supply that tie automatically.

Two original photographs improve local context:

- [PFF, original post 1, 5 May 2023](https://www.pff.de/thread/2817956-porsche-964-wagenheberaufnahme-vorne/?postID=155922679#post155922679)
  shows a damaged front receptacle's metal aperture inside a larger trim opening.
  Its year and C2/C4 configuration are not established.
- [Pelican, post 95 on page 5, 28 August 2018](https://forums.pelicanparts.com/porsche-964-993-technical-forum/983241-964-revival-after-15-years-storage-5.html)
  shows a rear support plate with four openings and underlying structure. The
  contributor reports a 1993 C2, without independent authentication.

Neither image has scale, a Mi F/G marker or a measured contact-mouth plane.
They do not identify which rear aperture is G or establish a donor match.
No reuse licence was observed; source photographs and document crops remain
private. The [review receipt](review.json) records hashes and claim limits.

## Whole-body context before aperture selection

Four broad inspection windows retain original source triangles around the
front/rear sill regions. They are search windows, never physical part contours:

| Window | Original triangles |
|---|---:|
| Front left | 93,328 |
| Front right | 88,931 |
| Rear left | 105,765 |
| Rear right | 170,289 |

The complete context contains 4,684,929 original triangles. Long arm-like
observations extend outside the body envelope near the four windows; front
views show disc/stem-like stacks below the broad body panel. Their shape and
arrangement are consistent with external lift/support hardware. This remains
an inference without an acquisition photograph or log identifying the objects.
Visible lower/outer surfaces do not reveal the upper contact interface.
Possible support occlusion must be considered alongside missing acquisition;
no specific hidden F/G aperture is asserted or reconstructed.

## Boundary loops are not automatically body holes

[audit_boundaries.py](audit_boundaries.py) recomputes original edge incidence
for eight selected, previously partitioned surface components. It checks their
complete boundaries against original open-edge rows and the original boundary
loop ID sets. Boundary-component IDs and surface-component IDs are different
namespaces. The fixed inputs are hash-admitted before and after the run.

In particular, boundary loop 1223 is the sole observed boundary of source
surface component 3 (5,744 triangles); loop 1431 is the sole observed boundary
of component 85 (4,376 triangles). These are not identified inner openings in
surrounding observed plates. Other reviewed components contain multiple
boundary cycles, but that alone supplies neither hole identity nor material.
Euler counts are retained as arithmetic only: vertex links, orientability,
genus and disk classification are not admitted.

Original open boundaries, artificial window cuts and unassigned loop IDs remain
visually distinct. An original boundary can still be a scan gap or physical rim.
The old `P17_cup`/`P19_ring` circle-fit labels are historical interpretations,
not independent authentication of body datums.

## Executed media and next gate

Local CPU inspection uses the original arrays with verified face/vertex ID
correspondence and no cleaning, filling, decimation or invented surfaces.
The [media receipt](media-receipt.json) records 29 stills and a five-second,
120-frame, 24 fps camera arc at 1600 × 1100. Original layers stay visible;
colours mark selected faces, not material. Decoded video frames 0, 60 and 119
were inspected. The complete final run is distinct from the first attempt's
metadata failure. These are diagnostic CPU VTK images, not native Omniverse
captures, material identification or a product validation result.

The media remains private under
`work/964-contact-context-20261106/runtime-001/render-003/`. Use
`WholeBody-underbody.png` for overall context and
`FrontLeftLayeredLoops-orbit/underbody-to-outboard.mp4` for the layered close-up.
Read the preserved private runtime recipe before recreating the stopped
container; it pins the image, 22 wheel versions/hashes and Debian packages.

The next admissible registration step still requires an independently labelled
measurement-point detail/photograph and visible original rim/contact evidence,
including assembly layers and uncertainty. The
[independent correspondence contract](../contact-registration-20261106/correspondence-contract.json)
remains in force. A fit cannot recover a surface hidden behind a support.

An alternative next inspection is the Mi D/E/H named fastener network: outer
front-crossmember heads D and outer transmission-crossmember heads H, with
inner heads E and an independently identified higher A/I/J contact for checks.
Bolt-head and bare-frame states must stay separate. Existing sill views do not
identify these fasteners; inspect actual front/rear assemblies before fitting.
No alternative source network itself admits scan points or a transform.

The boundary audit and five NumPy controls can be reproduced without source
geometry publication. The fixed private inputs must be present; use a fresh
output directory:

```sh
python3 twins/964-chassis/contact-context-20261106/audit_boundaries.py \
  --output work/964-contact-boundary-replay-new
python3 -m unittest discover -s tests -p test_964_contact_context.py -v
```

The [review receipt](review.json) also binds the independent Counter-based
recomputation of all eight selected components. It does not import the audit
author; exact face sets, original edge rows and disjoint exhaustive loop edges
were checked separately. No topology test establishes physical hole identity.

The [road/track evidence basis](approval-basis.md) separately records current
German and Swiss primary sources and the decisions needed before selecting
acceptance criteria. The full
[engineering and Omniverse goal ledger](../contact-registration-20261106/goal-ledger.json)
remains open; the [current progress ledger](progress-ledger.json) records the
new findings without changing that objective. This inspection releases no cell,
mould or structural result.
