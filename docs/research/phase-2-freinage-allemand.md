# Phase 2 — German-language research on braking

Date consulted: August 29, 2026.

## Decision

No braking component enters `catalog/components/` yet. The manufacturer
documents identify several discs, their application, their position and their
dimensions. They do not, however, give a net mass and do not describe a
complete material grade. Adding a mass taken from a retailer would violate the
twin's admission rule.

This decision does not call into question the commercial compatibility declared
by the manufacturers. It only means that the project's four mandatory fields —
size, mass, material and 993 application — are not all sourced.

## Qualified but incomplete references

| Position | Manufacturer reference | Cross-checked Porsche part number | Declared dimensions | Declared material | Blocking field |
|---|---|---|---|---|---|
| front left | Brembo `09.8420.11` | to be cross-checked before admission | Ø 304 x 32 mm, height 72 mm, centering 103 mm, 5 holes, minimum 30 mm | high carbon, vented | net mass, complete grade and direct Porsche part number |
| front right | Brembo `09.8421.11` | to be cross-checked before admission | Ø 304 x 32 mm, height 72 mm, centering 103 mm, 5 holes, minimum 30 mm | high carbon, vented | net mass, complete grade and direct Porsche part number |
| rear, quantity 2 | Brembo `09.C085.11` | to be cross-checked in the PET before admission | Ø 299 x 24 mm, height 65 mm, centering 103 mm, 5 holes, minimum 22 mm | high carbon, vented | net mass, complete grade and Porsche part number |
| front | ATE `24.0132-0142.1` | `993 351 043 01` | Ø 304 x 32 mm, height 72 mm, centering 103 mm, 5 holes, minimum 30 mm | high carbon, alloyed, vented | net mass and complete family/grade |
| front | ATE `24.0132-0143.1` | `993 351 044 01` | Ø 304 x 32 mm, height 72 mm, centering 103 mm, 5 holes, minimum 30 mm | high carbon, alloyed, vented | net mass and complete family/grade |

The ATE catalog contains a dimensional column `I`. The value `15,4` (15.4) on
the two 993 lines is a dimension of the disc drawing, not a weight. It must not
feed `physical.mass`.

## Sources retained

- [Brembo catalog for the 993 Carrera 3.8](https://www.bremboparts.com/europe/de/catalogue/porsche-911-993-3-8-carrera/000004674-1),
  manufacturer source for the application and dimensions of the three
  references;
- [Brembo `09.8421.11` data sheet](https://www.bremboparts.com/europe/de/catalogue/disc/09-8421-11),
  manufacturer source for the right side, the dimensions and the high-carbon
  designation;
- [ATE Classic Porsche catalog](https://www.ate.de/media/2826/atec3classic_2014-porsche.pdf),
  manufacturer source for the Porsche part numbers, the dimension diagram and
  the cross-check of the front dimensions.

The weight values shown by various shops were not retained: they are neither
published by the manufacturer nor accompanied by a weighing protocol, and they
may denote net weight, packaged weight or shipping weight.

## Exit gate

A reference may be admitted after obtaining one of the following:

1. a traceable manufacturer or TecDoc data sheet giving the net unit mass and
   the material;
2. a documented weighing of the exact reference, with instrument and
   uncertainty, supplemented by a manufacturer material declaration;
3. a measurement of an unambiguously identified OEM disc, with the Porsche part
   number and wear condition recorded.

Braking remains a safety-critical class: even if admitted into the digital
inventory, a component would be neither declared manufacturable nor released
without a professional engineering review and an approved validation plan.
