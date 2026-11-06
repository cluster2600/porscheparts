# Road and track validation basis — preliminary

Reviewed: 6 November 2026. The registration market is not yet selected; the
owner was asked to prioritise Germany, Switzerland or both. This note prepares
the two research paths. It establishes neither vehicle identity nor an accepted
approval route for replacing the original steel structure with a carbon cell.
The [programme](../../../docs/MONOCOQUE_964_993_PROGRAMME.md) remains a study.
The [source register](approval-sources.json) records acquisition methods,
editions, hashes where acquired and applicability limits.

## Current primary sources

For Germany, [StVZO §19(2)](https://www.gesetze-im-internet.de/stvzo_2012/__19.html)
identifies changes of vehicle category, expected danger to road users and
worsened emissions/noise as grounds for expiry of the operating permit.
[§21](https://www.gesetze-im-internet.de/stvzo_2012/__21.html) describes an
individual-vehicle application to the competent authority with a qualified
expert or designated technical-service report. The report's annex identifies the
applicable technical provisions; supporting test records must exist.

[TÜV Rheinland's modification guidance](https://www.tuv.com/germany/de/%C3%A4nderungsabnahme.html)
distinguishes approved-part installation checks from a report supporting an
individual permit where suitable part certificates are absent. This general
guidance does not establish the classification or acceptability of this
replacement monocoque. A project-specific determination is still needed.

For Switzerland, the official [OETV/VTS edition of 1 October 2026](https://www.fedlex.admin.ch/eli/cc/1995/4425_4425_4425/fr)
was acquired from the [official PDF](https://www.fedlex.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/1995/4425_4425_4425/20261001/fr/pdf-a/fedlex-data-admin-ch-eli-cc-1995-4425_4425_4425-20261001-fr-pdf-a.pdf).
Article 4(3), page 6, addresses substantial modifications under the law applying
at the subsequent examination and explicitly includes whole-body replacement.
Article 34(2), pages 33–34, requires notification and subsequent inspection of
modified vehicles. Article 34b(3), page 35, permits referral of technical checks
to a recognised testing body. Older web copies citing the applicable-law rule
as Article 3b must not replace the current text: current Article 3b concerns
international transitional provisions.

The [asa index](https://asa.ch/online-bibliothek/richtlinien/) links its current
view-only guideline 2a. Its detailed classification has not been extracted or
accepted for this project. A [cantonal authority's explanation](https://ar.ch/verwaltung/departement-inneres-und-sicherheit/strassenverkehrsamt/fahrzeugpruefungen/technische-aenderungen/)
distinguishes cases requiring authority review, manufacturer declarations,
recognised testing-body evidence or approval. No category is assigned here.
[DTC's structural-modification service](https://www.dtc-ag.ch/dienstleistungen/aktive-sicherheit/abaenderungspruefung/aenderung-der-tragenden-struktur)
lists torsional stiffness, bending stiffness, vehicle dynamics and durability
investigations. That is a relevant capability lead, not a quotation, scheduled
test or confirmation that it will approve this project.

## Decisions needed before a final acceptance specification

The responsible authority/technical service must determine the treatment of the
replacement structure, retained vehicle identity, applicable regulatory dates,
vehicle category and permitted variants. Do not assume that the original 964
registration or a later 993 component automatically transfers to the new cell.
Keep any vehicle identifiers and personal registration documents private.

The following is the programme's engineering evidence agenda, not an assertion
that every row is a prescribed legal test in both markets:

| Area | Evidence to agree and produce | Current gap |
|---|---|---|
| Configuration | Exact body, year, drivetrain, gearbox, seats and use; change list | C2 is owner-reported; year/gearbox and market unresolved |
| Attachment/load paths | Measured common-frame interfaces, axes, mating faces, joint loads and tolerances | No admitted donor registration |
| Global structure | Defined torsion/bending fixtures, physical reference, correlated model and convergence | No accepted reference-body test or cell model |
| Composite failure and durability | Laminate/core/adhesive/insert data, coupons, joints, damage mechanisms, fatigue and environmental conditioning | Materials/process and acceptance limits missing |
| Occupant and vehicle systems | Applicable restraint, seat, steering, suspension and impact/rollover evidence | Requirements and test applicability to be determined |
| Manufacturing | Mould/access review, drape/cure/residual-stress inputs, process witnesses and inspection plan | Part/mould geometry and qualified process missing |
| Digital evidence | Traceable geometry/results, units/axes, final USD checks and native Omniverse review | Current diagnostic meshes are not a validated cell |

Track use also needs a defined use case. A track-day operator's conditions and
a competition class's technical rules are separate applicability questions;
no FIA eligibility or circuit release is established. The owner/engineer must
specify events, tyres, speeds and duty cycles before accepting track load cases.

The approximately 1200 kg vehicle input supplies neither permissible axle
loads nor a complete structural test specification. An Omniverse render or a
successful solver execution supplies no approval decision.
