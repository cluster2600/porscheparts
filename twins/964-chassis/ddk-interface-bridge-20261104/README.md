# DDK leads connected to the 964 interface and scan registers

**Result, 4 November 2026:** 15 selected facts from nine original forum posts
are now cross-referenced with the existing 18 manual point identities,
19 transverse span observations and seven scan search regions. The source
posts were read, not just their extracted catalogue rows. **None supplies a
new qualified 964 attachment XYZ, tunnel surface or structural load.**

The deliverable is a reviewable bridge between sources and engineering inputs:
[reviewed facts and source receipts](reviewed-leads.json), the generated
[crosswalk](bridge.json), and a [19-row survey sheet](interface-crosswalk.csv).
The sheet preserves both P14 model-year families and leaves all coordinates,
axes and mating faces blank. Context links identify where to investigate;
they do not identify a particular scan feature or establish interchangeability.

## Corpus and scope

The PorscheFanatics import at commit
`b437b119fd1168b38ea3c613b4c1c027fb3dfd0c` contains 5,916 measurements.
There are 139 unique records tagged 964 or 993: 21 labelled owner-measured,
23 quoted and 95 reported. These provenance labels are not metrology acceptance.
Their categories include 26 dimensions, 31 masses and 11 ride heights; many
dimensions concern small items or tools rather than body construction.

Selection followed a generation-tag and structural-keyword screen. This is
not an exhaustive reading of all records or forum threads. The retained raw
dataset SHA-256 is
`8a288acd49ff46123ba51cc6d482e582ee47e0e71173bab41896c9445a7b15a5`.
The public [964](https://porschefanatics.com/owner-measurements/964/) and
[993](https://porschefanatics.com/owner-measurements/993/) pages assign shared
records to their first generation tag, so their page totals differ from this
union of tags.

## What the original sources actually support

All numbers below are source claims, not newly accepted design dimensions.

| Source | Finding | Consequence for this monocoque |
|---|---|---|
| [Celette measurements, post 562973](https://www.ddk-online.com/phpBB2/viewtopic.php?p=562973#p562973) | Three reported heights, 111/96/91 mm, measured to fixing-hole centre lines relative to a 108 mm rear reference; the owner estimates +/-0.5 mm in Z | Front-suspension investigation context for P3/P5/P6 only. Generation, exact hole identities and the transform to our datum are unconfirmed. The linked drawing returned HTTP 404. |
| [Engine/gearbox spacing, post 58292](https://www.ddk-online.com/phpBB2/viewtopic.php?p=58292#p58292) | The reply quotes 1144 +/-0.5 mm; the opening post explicitly identifies a 1972 car | Excluded from the 964/993 dimensional contract. Do not use it to close P12/P15/P21. |
| [Glazing, post 149001](https://www.ddk-online.com/phpBB2/viewtopic.php?p=149001#p149001) | A reported change from 10 to 15 mm aperture flange during MY1989, associated with the 964 glazing system | Add an exact glass/seal/flange interface check. Width alone provides neither aperture shape nor a structural glazing joint. |
| [Heating, post 446125](https://www.ddk-online.com/phpBB2/viewtopic.php?p=446125#p446125) | Reported 80 mm hoses in the front cockpit corners | Front-services routing lead, not a cut-out diameter or a known path through the new bulkhead. |
| [Engine envelope, post 314416](https://www.ddk-online.com/phpBB2/viewtopic.php?p=314416#p314416) | Reported 993 engine width of 840 mm, discussed against an 815 mm race-car rail gap; 964 width is explicitly unknown | A separate 993 packaging investigation. No 964 dimensions, accessory configuration, mounts or swept clearance are established. |
| [Mixed drivetrain, post 568672](https://www.ddk-online.com/phpBB2/viewtopic.php?p=568672#p568672) | Approximately 30 mm mismatch for a 964 engine in an SC shell with a 930 four-speed gearbox | Conversion-specific exclusion, not a 30 mm adjustment to the 964 engine mounts. |
| [Shift access, post 216488](https://www.ddk-online.com/phpBB2/viewtopic.php?p=216488#p216488) | A 150 x 150 mm hatch in a 901/911 transmission discussion that also mentions a 915 installation | Do not transfer the hatch into the donor's unidentified gearbox configuration. Add linkage adjustment and maintenance access to the tunnel survey. |
| [Engine masses, post 326009](https://www.ddk-online.com/phpBB2/viewtopic.php?p=326009#p326009) | Four quoted configurations: 964 276 kg, 964 RS 226 kg, 993 232 kg, 993 RS Varioram 221 kg; all attributed to another forum | Configuration-specific leads, not four independent weighings. Accessories and flywheel differ. No accepted mass, centre of gravity or support reactions result. |
| [Vehicle masses, post 648311](https://www.ddk-online.com/phpBB2/viewtopic.php?p=648311#p648311) | A comparison table reports 1350 kg for a 964 C2 and 1390 kg for a 993 C2 | No weighing procedure or load state. The user's 1200 kg remains a design target, not a measured mass or an approved test load. |

The three Celette dimensions share a measurement session. The four engine
masses share a secondary citation. More rows do not constitute independent
corroboration. Neither the source drawings, cited workshop manual nor the
upstream engine weighing records were recovered in this increment.

## Consequences by part of the cell

| Review area | Existing reference and load path | Work now specified | Acceptance still needed |
|---|---|---|---|
| Front attachments | Manual P3/P5/P6; front transition search; suspension loads into bulkhead and sills | Resolve the Celette feature identities against the manual instead of copying Z values | Same-variant XYZ, axes, bearing faces, reference-plane transform and uncertainties |
| Tunnel and footwells | CentralRouteSearch and two floor searches; floor/tunnel/bulkhead continuity | Keep lower cover, body tunnel, installed linkage and maintenance access as four distinct survey objects | Interior sections, identified joins and openings, exact gearbox, moving and service envelopes |
| Front services | Front transition and footwell searches | Locate heater hose ends, routes and clearance needs | Same-donor installed route and connection dimensions; no automatic 80 mm hole |
| Rear bulkhead and powertrain | P12/P15/P21; rear transition search; powertrain reaction path into the cell | Exclude early-car spacing and mixed-drivetrain offset; keep 964/993 packaging separate | Exact mount identities, coordinates, mating faces, accessory envelope, mass/CG and reaction cases |
| Glazing and upper cell | No acquired upper-cell geometry in these scan regions | Identify the glass, seal and flange family and its relationship to the roof and pillars | Measured aperture and joint surfaces; this lead supplies no roof/pillar section |
| Sills, doors and restraints | Two unidentified sill searches; sill/bulkhead/upper-cell load paths | Preserve the existing missing-interface entries; no selected DDK fact closes them | Identified layers, seams, inner section, door and restraint attachments |

The scan crosswalk carries the existing source-face-ID hashes, not newly
invented surfaces. The seven search windows are geometric selections, not
seven identified vehicle parts. The unselected Context remains in the upstream
scan and is not counted as an eighth search region. In particular,
CentralRouteSearch remains a **lower-cover candidate**, not the tunnel's
interior wall. Its rectangular selection edges are not part contours.

The [component identity review](../monocoque/component-review-20261029/README.md),
[boundary audit](../monocoque/observed-boundaries-20261029/README.md),
[current interface contract](../interface-exploitation-20261030/contract.json)
and [survey plan](../interface-measurement-plan.md) remain authoritative.
The existing [CAE shifter source](../../../catalog/sources/src-cae-964-c2-993-shifter-installation.json)
adds exact-variant routing context; its racing retrofit is not factory geometry.

## Verification and reproduction

`build.py` checks the donor, source links, point and search-region membership,
unknown coordinates, scan admission and fact fields before publishing the
crosswalk. It records input and builder hashes. It cannot promote a lead to
CAD or a load input. This is an executable guard for **this documentary bridge**,
not a new gate wired into every historical CAD or solver script.

```sh
python3 twins/964-chassis/ddk-interface-bridge-20261104/build.py --check
python3 -m unittest discover -s tests -p 'test_964*interface*.py' -v
```

For the private source comparison, add
`--dataset /path/to/forum-measurements.json`. That check admits the exact
dataset hash, recomputes coverage and compares each retained fact and URL;
it never copies member identity fields or raw posts into the repository.
The nine cached original pages are retained privately by hash. No image
redistribution or training right is inferred from public accessibility.

The regression checks exercise false promotion, wrong gearbox assumptions,
unknown points/regions, duplicate records, non-finite values, member-identity
fields and a substituted dataset. They also reproduce the 19-row sheet and
preserve both P14 spans. Passing these checks does not prove vehicle fit or
strength. No geometry, laminate, torsion, manufacturing or Omniverse result
is generated by this increment.

This implements R-PROVENANCE and R-CHANGE in the
[engineering governance](../../../docs/architecture/migration-verification.md).
It preserves the current `F1_envelope` level and the separate 993/C4 work.
