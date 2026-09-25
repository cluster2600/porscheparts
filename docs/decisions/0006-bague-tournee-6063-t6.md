# 0006 — The ring will be turned from 6063 T6

Date: 2026-09-11

Direct follow-up to [0005](0005-alsi10mg-nest-pas-un-choix.md), which found that
the ring's AlSi10Mg had never been chosen.

## Decision

Manufacture `993-INT-SWITCH-TRIM-RING-F1-0001` by **turning from EN AW-6063 T6
bar stock**, with a clear bright-anodized finish. `preferred_process` changes
from `undecided` to `CNC`. LPBF stays in the catalogue as a screened candidate —
steps 02, 03 and 04 keep their documentary value — but it is no longer the
chosen route.

## The real trade-off

The criterion that governs this part is appearance. On that criterion, the two
candidate grades pull in opposite directions.

| | 6063 T6 | 6061 T6 |
|---|---|---|
| bright anodizing | **reference grade**, low iron content, uniform surface | adequate, without the architectural quality |
| turning | soft and gummy, long stringy chips | noticeably more pleasant, short chips |
| strength | sufficient — the part carries nothing | higher, of no use here |

6063 wins because the only real requirement is the one where it is best, and
because its weakness — machinability — is a parameter constraint, not an
impossibility: uncoated carbide tool, sharp polished edge, high cutting speed.
This instruction is passed on to the turner, who may contradict it; the quote
explicitly asks for 6061 T6 priced alongside.

6262 T6511, developed for machinability through added bismuth and lead, is set
aside: lead falls under the end-of-life vehicles directive and its exemptions, a
question this repository has not investigated.

## What changing the process did not solve

This is the important point. The turning route has **five closed gates** versus
seven for LPBF, but the two that matter are the same as before:

- **the fit dimension is not toleranced** — the Ø30.5 mm comes from a sales page
  for an aftermarket ring, not from a measurement of the housing;
- **the edges are not defined** — the master has sharp edges, and a decorative
  ring is judged first on its front edge.

Added to these are workholding on a 1.25 mm wall, i.e. 4.1% of the outside
diameter, and anodizing growth of 5 to 15 µm, of the same order as the
clearance sought.

## The proposed way out for the fit dimension

On a turned part, the second and third pieces cost a fraction of the first. The
quote therefore asks for **three bare, non-anodized rings, at Ø30.40, Ø30.50 and
Ø30.60 mm**. They are tried, the right one is kept, and only that one is
anodized, subtracting the coating thickness at that point.

This does not replace the measurement of the housing, which remains to be done.
It makes it possible to move forward without vehicle metrology, which is
different.

## Accepted limitation

The ring's original grade remains unknown. 6063 T6 is the repository's choice,
based on the appearance criterion, not an identification of the commercial part.
Nothing that comes out of this quote conforms to the original, and nothing is
authorized for fitting.
