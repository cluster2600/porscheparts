# PET identity of the 993 dashboard trim

Decision record for issue #566, prepared 2026-11-06. The machine-readable
matrix is [`pet-identity.json`](pet-identity.json), and
`scripts/check_993_dashboard_pet_identity.py --check` keeps it and the part
record consistent.

**Status: awaiting independent review.** This is a documentary audit. It
establishes no geometry, fit, occupant-safety or manufacturing property. It
does not authorise acquiring a car, a trim or a document.

## Source

Porsche Classic Genuine Parts Catalogue, 911 (993) 1994-1998, Kat 017
(`SRC-PORSCHE-PET-993`), 674 pages, SHA-256
`b67cf3586f9a92bee5ccc8e84462515231c84ddd23c610e4a2e739fedb1166aa`, downloaded
2026-11-06. The third-party copy the record cited before (`SRC-PET-993-KAT17-PDF`)
has the same bytes, so its page numbers are the same.

Rights: Porsche AG, reference only. This record keeps part numbers, positions,
plate titles and remark codes, which are identification facts. It copies no
illustration, page image or excerpt.

The page 14 legend reads `/LL` as left-hand drive, `/RL` as right-hand drive,
and `/L` and `/R` as left and right in the direction of travel.

## Finding

| Option code | Hand | Plate | Dashboard trim | Knee protection strips (left, right) | Mapping |
|---|---|---|---|---|---|
| M564, non-RS | LHD | none | **null** | **null** | unmapped in Kat 017 |
| M564, non-RS | RHD | none | **null** | **null** | unmapped in Kat 017 |
| M561 | LHD / RHD | none | null | null | unmapped in Kat 017 |
| M562 | LHD | 809-00, p. 501 | 993 552 055 00, 055 01 | 809-01, p. 505 | title match only, out of scope |
| M562 | RHD | 809-00, p. 501 | 993 552 056 00, 056 01 | 809-01, p. 505 | title match only, out of scope |
| M002 | LHD | 809-02, p. 511 | 993 552 055 00 | 911 552 069 00, 911 552 070 00 | option code on the line |
| M002 | RHD | 809-02, p. 511 | 993 552 056 00 | 911 552 069 01, 911 552 070 01 | option code on the line |
| M003 | LHD | 809-02, p. 511 | 993 552 055 70 | 964 552 077 70, 964 552 078 70 | option code on the line |
| M003 | RHD | 809-02, p. 511 | 993 552 056 70 | 964 552 077 71, 964 552 078 71 | option code on the line |

Three facts drive the table.

1. **The only non-RS dashboard plate is for cars with a passenger airbag.**
   Illustration 809-00 is titled "Dashboard, for cars with Airbag, Passenger's
   side". None of its lines carries an option code. Its position 11 is the
   passenger airbag unit, which group 4/03/06 lists as `993 803 071 00` /LL and
   `993 803 072 00` /RL (page 263).
2. **The no-airbag plate is restricted to the Carrera RS.** Illustration 809-02
   reads "Dashboard, Knee protection strip, for cars without Airbag,
   Passenger's side", has CARRERA RS in the model column, and puts M002 or
   M003 on every trim and knee-strip line.
3. **No plate names a non-RS M564 car.** Apart from the option list, M564
   appears in Kat 017 only on illustration 403-07, for the steering shaft.

So the M564 left-hand-drive F0 target has **no part number from Kat 017**. It
stays null. The part number is not borrowed from the RS plate, and it is not
borrowed from the airbag plate.

## The `055/056 00` conflict (CTR-0019, open)

`993 552 055 00` /LL and `993 552 056 00` /RL appear both on 809-00 (with
passenger airbag) and on 809-02 under M002 (without). Two explanations fit the
text:

- **H1:** the trim is common to both installations and has no deployment flap.
  On airbag cars, separate parts would close the opening: 809-00 lists
  "Lid, Upper part" `993 552 088 00` (position 13) and "Lid, Lower part"
  `993 552 090 00` (position 14, page 502), and 809-02 lists neither.
- **H2:** the number is shared in the catalogue, but the physical parts differ
  by production period or market, or one plate is wrong.

**Neither is adopted.** H1 would relax an occupant-restraint exclusion on
catalogue text alone. A real specimen can separate them through the
passenger-side reverse inspection (E2 below), and so can a Porsche technical
document that states the trim's airbag provisions.

## What changed in the part record

- The variant label now reads "M564 without airbag (trim number unmapped in
  PET Kat 017)".
- The PET source now points at the official copy, with its hash, and states
  what both plates list.
- The knee-strip limit used to call the 809-01 airbag-plate strips "series
  production". It also gave only the left-hand-drive M003 pair and missed the
  M002 strips. It now gives the plate-level mapping.
- A new limit states the identity verdict and the admission rule.

Nothing else changed. `validation.status` stays `concept`,
`safety_class` stays `functional`, and the passenger-airbag exclusion stays in
force.

## Same-specimen protocol

No measurement of a dashboard trim is admitted until the specimen passes all
five checks. The specimen ID has the form `SPEC-993-DASH-NNNN`. The repository
assigns it in sequence, and it is never derived from a VIN, chassis number,
registration, owner, place or listing.

| Evidence | What is submitted | Admission rule |
|---|---|---|
| E1 option label | Photograph of the option label with VIN, chassis number and owner or dealer data masked before it leaves the contributor; transcription of every M-code | Refused if any identifier is visible or M562 is listed. Held if M561 is listed, or if none of M561/M562/M564/M002/M003 is |
| E2 passenger reverse | Photographs with a scale of the passenger-side back face and the space above the glovebox: airbag module, moulded tear line, deployment flap, lids `993 552 088 00` / `090 00` | Refused if any module, tear line or flap is seen, whatever E1 says, or if the region is not shown |
| E3 trim label | Transcription and photograph of any part number on the removed trim, or a statement that none was found | A label that disagrees with the matrix opens a contradiction. It never overwrites the matrix |
| E4 continuity | Hash manifest of every file under the specimen ID; at least two marks (crack, repair, wear) photographed both installed and removed | Refused if a file lacks the ID or a hash, or if the two states cannot be linked |
| E5 rights | Contributor's written licence to keep and publish the images; confirmation that no personal data remains | Refused without it |

`admit_specimen()` in the checker is a preflight. It refuses explicit
exclusions, and at best returns `held` for a complete submission, because it
cannot verify off-repository photographs, hashes, continuity or rights. The
independent measurement and rights/privacy reviewers verify those and record
the admission. An admitted specimen
establishes the identity and airbag state of that specimen only. A trim label
read on it is not a catalogue mapping for M564.

## Not done here

- No interface, datum or measurement contract. That is issue #567, and it
  starts from this matrix.
- No change to `twins/993-dashboard-f0/assembly.json`, which is still in an
  open pull request. Its M564 trim number is already null, which agrees with
  this audit.
- No model years per variant. Every page carries the catalogue header "Model
  life 1994>>1998", and no trim line has a year remark. Null means "not stated
  in Kat 017".
- No supersession. Kat 017 states none for these trims.
