# Owner-supplied frame dimensions — 5 November 2026

**Acquisition result:** `frame_data.zip` supplies 15 readable technical files,
covering 19 pages. The earlier lack of readable nominal body-point data is now
partly resolved. The [catalogue record](../../../catalog/measurements/MEAS-OWNER-964-FRAME-20261105.json)
contains 57 bounded documentary entries: 23 CH coordinate rows, 14 Mi contact
height/coordinate rows and 20 Coupe opening spans. These are source-local nominal
references. Registration to the owner's scan remains to be established.

The supplied body manual has the **same 260 technical scan images** as the held
copy: extracted image bytes and decoded pixels match in the same page order and
resolution. The different PDF hash reflects the removal of navigation overlays.
There are no additional manual dimensions. PDF pages 7–9 still correspond to
50-03, 50-05 and 50-05a.

## Source coverage and identity

[The intake manifest](intake.json) records both input hashes, every archive
member, its page count, digest and visual review. All 19 archive pages were
inspected; numerical transcription is bounded, not exhaustive. Documents were
read as evidence; document instructions did not control agent actions.

| Family | Files / pages | Observed applicability | Treatment |
|---|---:|---|---|
| Ar | 2 / 4 | Carrera 2/4 Coupe from 1989; separate 1989–94 Cabriolet, revision 05-98 | Longitudinal/width numbers readable; height/setup rows need their tool legend |
| CH | 2 / 4 | Explicit 1992 Carrera 2, **964 330 Coupe** / **964 630 Cabrio**, PO10E, 9/97 | Separate parts-on and parts-removed coordinate networks |
| Ed | 6 / 6 | Coupe/Cabriolet folders and body illustrations; cropped leaves lack the model/year title | Snap-on copyright visible; 14 heights and longitudinal stations retained as a separate partial transcription |
| Mi | 4 / 4 | Explicit 1992 Carrera 2/4 Coupe & Turbo Coupe; separate Carrera 2/4 Cabriolet | Contact legend, datum line, metric wheelbase, projected dimensions and upperbody control spans |
| Other | 1 / 1 | PORSCHE 911 1989–94, sheet 92-40 | Readable additional frame diagram; not merged with the other point-number systems |

Folder abbreviations do not establish publisher identity. Only the Ed leaves
visibly identify Snap-on. CH/Ar omit an explicit unit label; millimetres are an
interpretation supported by scale and the 2272 wheelbase. Mi Fig. 1 explicitly
prints a metric wheelbase and a half-width convention. Source tolerances,
metrological uncertainties and a commercial reuse licence are not supplied.
Original PDFs, JPGs and ZIP bytes remain private and were not uploaded.

## CH source-local coordinates and independent spatial checks

CH provides 13 station rows with parts on and 10 with parts removed. X below is
calculated from the printed **projected longitudinal chain**, choosing point 5
as zero and rearward as positive. Y is the printed half-width magnitude, not a
registered physical side. Z is the printed height; the physical datum setup is
not identified. All components use the interpreted millimetre convention.

| Contact state | Local point | X from point 5 | Half-width | Height |
|---|---:|---:|---:|---:|
| Parts on | 5 | 0 | 390 | 369 |
| Parts on | 9 | 873 | 385 | 147 |
| Parts on | 11 | 2446 | 217 | 127 |
| Parts on | 15 | 3648 | 499 | 328 |
| Parts removed | 5 | 0 | 390 | 369 |
| Parts removed | 9 | 873 | 385 | 219 |
| Parts removed | 11 | 2446 | 217 | 149 |
| Parts removed | 15 | 3648 | 499 | 334 |

For a same-side direct length, use differences in X, half-width and height.
For a cross-body diagonal, use the **sum** of the half-widths. The twelve
resulting CH distances all round to the independently printed integers. This
also explains why a direct length must not substitute for a projected X span.
For example, point 5–9 is **901** with parts on and **886** after removal; the
projected X separation is **873** in both states.

The corresponding CH Coupe/Cabrio image content below the title is pixel-identical.
This documents the supplied publisher coverage; it does not establish universal
physical interchangeability. CH point 9 is not automatically Porsche manual P9.

## Mi contacts and upperbody openings

Mi Fig. 1 defines ten contacts A–J, including bolt heads, a strut stud tip and
25 × 34 mm hole centres. Its source datum line and centreline are visible.
Four points provide different bolt and bare-frame heights: B **167/237**, D
**164/246**, E **173/193**, H **151/187**. The 14 rows preserve those contact
definitions. Widths B/C/I stay unknown; C/I refer to missing back-page information.
F is chosen as the separate Mi X origin. No CH-to-Mi transform is assumed.

Six Mi same-side/cross-body lengths also close to their printed integer values.
All **18** spatial checks pass, with a maximum residual of **0.493922 source
units**, interpreted as mm. This is nominal rounding consistency, **not** a
measurement accuracy or engineering tolerance.

Twenty Coupe upperbody spans are retained with endpoint definitions. Examples:
front windshield radius-centre spans A–B **1060**, D–C **1350**, D–B **1302**;
rear window **955 / 913 / 1125**; door opening F–C **1045**. These are control
features, not glass dimensions or continuous opening curves. Cabriolet upperbody
values differ and remain separate. Mi H's **436** bolt span cannot replace the
manual P12's **278** body-hole span; the contacts differ.

Ar's setup numbers are not converted to Z. Ed point 4's printed **763** height
is retained after tracing its leader to the high strut area. No number is repaired
from its apparent location on the page or averaged across sources.

## Reproducible outputs and next geometry gate

- [source-data.json](source-data.json): reviewed source numbers, assembly states,
  contact definitions, unit interpretation and unknowns.
- [source-coordinates.csv](source-coordinates.csv): 37 component rows; unknown
  Mi widths are blank, not inferred. CH and Mi retain separate origins.
- [closure.json](closure.json): 18 independently printed spatial redundancies.
- [source-frame.svg](source-frame.svg): CH measurement landmarks only; no body
  outline or hidden surface is inferred.

Run `python3 twins/964-chassis/owner-frame-data-20261105/build.py --check`.
Six focused tests detect state mixing, using a direct length as a projection,
unknown-width propagation and stale outputs. The upstream verdict permits
documentary arithmetic; it blocks using this network as registered donor geometry.

The next work is to identify the corresponding physical features in the existing
underside scan, verify their contact state and fit a common datum using redundant
points. Retain the donor's unconfirmed year and gearbox. Source points must be
matched by physical feature, not number or coincident span. Obtain missing width
definitions and system legends where needed. The 993 needs its own equivalent
data; these supplied leaves do not establish 993 compatibility.

The [existing engineering interface contract](../interface-exploitation-20261030/contract.json)
keeps its donor XYZ, axes and mating faces unadmitted. Hidden tunnel sections,
service/drivetrain envelopes, composite properties, joints, mould/process inputs
and physical correlation remain open. This packet advances the nominal reference
network; structural, manufacturing and Omniverse validation have not been performed.
