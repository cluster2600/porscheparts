# Phase 1 — German research, batch 1

Date accessed: August 29, 2026.

## Scope

This first wave targets the official technical sources of the German market and
the public geometry attributed to the Porsche 993. The queries were phrased in
German, in particular:

- `Porsche 993 Ersatzteilkatalog technische Dokumentation`
- `Porsche 993 3D Scan CAD Modell STL Lizenz`
- `Porsche 993 Karosserie Punktwolke CAD`
- `Porsche 993 Maße Toleranzen Reparaturleitfaden`
- `Porsche 993 3D Druck Ersatzteile`

Third-party files were not downloaded into the repository. A license declared
by a secondary index remains to be confirmed on the original publication.

## Direct results

1. The [official 993 PET](../../catalog/sources/src-porsche-pet-993.json) is a
   674-page PDF covering Carrera, Carrera S, Carrera 4/4S, Carrera RS,
   Cabriolet, Targa and Turbo. It provides part numbers, variants and exploded
   views, but no dimensioned manufacturing geometry.
2. The [German literature catalog](../../catalog/sources/src-porsche-literature-catalogue-de.json)
   confirms the part numbers of the German repair guides and OBD-II guides for
   Carrera and Turbo. It does not contain the guides themselves.
3. The [technical literature shop](../../catalog/sources/src-porsche-technical-literature-de.json)
   offers, among others, books on types, dimensions and tolerances.
   Copyrighted or paid publications stay out of the repository.
4. The [German Parts Finder](../../catalog/sources/src-porsche-classic-partsfinder-de.json)
   is used to date price and availability. A lack of results does not prove
   that a part is discontinued.
5. Nine community 993 assets were found with author, declared license, number
   of files and declared dimensions. None has yet had an independent
   dimensional check.

The search found no complete 993 scan that is freely redistributable and comes
with demonstrated metrological accuracy. The commercial body models found are
mainly visualization meshes; they do not replace measuring a part.

## Targeted wave: frame bench and workshop manual

A second wave reran the queries `frame data`, `body dimensions`, `Celette`,
`Group 5`, `Running Gear`, `KATALOG_993` and their German equivalents
`Karosseriemaße`, `Richtbankdaten`, `Richtsatz` and `Reparaturleitfaden`.

- Volume V of the [official workshop manual](../../catalog/sources/src-porsche-workshop-manual-993.json)
  contains the construction dimensions, the body shell repair dimensions and
  the floor pan dimensions. Volume IV covers the running gear.
- The complete copies spotted on Cannell, PDFCoffee, Scribd and through private
  forum exchanges have no demonstrated distribution right. They are neither
  downloaded nor referenced as usable sources.
- A [Celette MZx 964/993 bench jig set](../../catalog/sources/src-celette-mzx-964-993-jigs.json)
  is confirmed by the manufacturer. It is intended for holding and measuring,
  without pulling operations, but its public listing reveals no coordinates.
- [Car-O-Data](../../catalog/sources/src-car-o-liner-car-o-data.json) contains
  professional upper and lower body shell measurement sheets. The existence of
  a 993 sheet is not publicly confirmed.
- The query `site:porsche.com "KATALOG_993" filetype:pdf` did not find a better
  PET than the official Kat 017 already recorded.

Conclusion: the most credible path to the body shell geometry is the official
volume V or supervised access to a professional frame bench database. A PDF
copy found through Google is not, by itself, a legally reusable source.

## Matrix of the twenty candidates

`D` here means a community or visual reference without demonstrated accuracy.
`PET` means that only the identity of the part is confirmed: the geometry must
be measured or legally reconstructed.

| # | Candidate | Origin | Current evidence | Gap before CAD or prototype | Priority |
|---:|---|---|---|---|---|
| 1 | Pollen filter cover tab | [Asset](../../catalog/sources/src-renn3d-pollen-filter-cover-tabs.json) | 4 STL, photos, CC-BY declared, level D | Exact license, measurement and 993 fit | High |
| 2 | Console switch cover tab | [Asset](../../catalog/sources/src-renn3d-console-switch-tab-repair.json) | 1 STL, photo, CC-BY declared, level D | Exact license and 993 fit | High |
| 3 | Console cup holder | [Asset](../../catalog/sources/src-renn3d-center-console-cup-holder.json) | 1 STL, fitted photo, public domain declared, level D | Confirm rights, variant and interferences | High |
| 4 | Phone mount on 82 mm gauge | [Asset](../../catalog/sources/src-renn3d-gauge-ring-phone-mount.json) | 1 STL, CC-BY declared, level D | Trademark risk on the bezel, and stability | Medium |
| 5 | 4x6 speaker adapter frames | [Asset](../../catalog/sources/src-renn3d-hifi-speaker-adapter-frames.json) | 2 STL, public domain declared, level D | Published scale obviously inconsistent | Blocked |
| 6 | Custom rear grille bar | [Asset](../../catalog/sources/src-renn3d-custom-split-grille-bar.json) | 3 STL, CC-BY-NC-SA declared, level D | Not OEM, non-commercial, fit to be confirmed | Low |
| 7 | Rear main seal installation tool | [Asset](../../catalog/sources/src-renn3d-rear-main-seal-tool.json) | 4 STL, CC-BY-SA declared, level D | Functional dimensions and workshop procedure | Medium |
| 8 | Seat back release button | [Asset](../../catalog/sources/src-renn3d-seat-back-release-button.json) | 1 STL, OEM part numbers declared, level D | Seat safety review and compatibility | Blocked |
| 9 | Remote clutch bleeder bracket | [Asset](../../catalog/sources/src-renn3d-remote-clutch-bleeder-bracket.json) | 2 STL, CC-BY-NC declared, level D | Proximity to the clutch system, safety review | Blocked |
| 10 | Interior sensor cover, `993 659 147 00` | PET, plate 813-40 | Official part number, 1996 and later | Measurable original, clips and material | High |
| 11 | HVAC knob, `993 659 146 00` | PET, plate 813-40 | Official part number | Measurable original, indexing and material | High |
| 12 | HVAC knob, `993 659 145 00` | PET, plate 813-40 | Official part number | Measurable original, indexing and material | High |
| 13 | HVAC knob, `944 653 205 00` | PET, plate 813-40 | Official part number, quantity 2 | Shared compatibility and measurable original | High |
| 14 | Lighting knob, `993 613 055 00` | PET, plate 903-06 | Official part number | Interface with the switch, separate symbol | High |
| 15 | Lighting cap, `993 613 250 00` | PET, plate 903-06 | Official part number | Geometry, pictogram and thermal resistance | Medium |
| 16 | Defrost cap, `993 613 253 00` | PET, plate 903-06 | Official part number | Geometry, pictogram and translucency | Medium |
| 17 | Front fog light cap, `993 613 251 00` | PET, plate 903-06 | Official part number | Geometry, pictogram and translucency | Medium |
| 18 | Rear fog light cap, `993 613 252 00` | PET, plate 903-06 | Official part number | Geometry, pictogram and translucency | Medium |
| 19 | Steering column cover, `993 552 277 00` | PET, plate 903-10 | Official part number | Variant, fasteners and clearance with the controls | Medium |
| 20 | M490 speaker grille, `993 555 777 00` | PET, plate 911-05 | Official part number, quantity 2 | Original, acoustics, texture and fitting | Medium |

## Gaps and decisions

| Question | State | Project decision |
|---|---|---|
| Open, metrological complete 993 scan | Not found | Do not build the twin from an artistic mesh |
| Exact license of the community assets | Often declared by a secondary index | Check the original page before any import |
| Dimensions of the PET candidates | Absent from the exploded views | Measure an original or its surroundings |
| Current commercial availability | Not audited part by part | Use the Parts Finder with a date and otherwise keep `unknown` |
| First titanium part | Outside this wave | Wait for mechanical needs, loads and a demonstrated material benefit |

## Next gate

For the three high-priority candidates derived from assets, the next action is
to check the original publication, then to create a part record only after
obtaining a specimen or reproducible measurements. For the PET candidates, the
part or its housing must be photographed and measured with the repository's
measurement template.
