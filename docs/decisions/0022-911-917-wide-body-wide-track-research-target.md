# ADR 0022 — 911-917 packaging: wide body, wide track as the F15+ research target

## Status

Accepted by the project owner on 2026-11-09 for
[issue #464](https://github.com/cluster2600/porscheparts/issues/464), choosing
option 1 of the options prepared on that issue on 2026-11-06. This is a
research direction, not a selected layout, a fitment claim or a release.

## Context

The F14 rear-driveline trial ([INTEGRATION.md](../../twins/vehicle-911-917/INTEGRATION.md),
rerun 2026-10-12) showed that the baseline track makes the drive shafts and the
frame collide, while the trial track clears them but puts the tires outside the
documentary body width:

| Envelope | Value | Status |
|---|---|---|
| Body width | 1,735 mm | documentary (993 workshop manual p.19) |
| Rear track: baseline / F14 trial | 1,444 / 1,840 mm | manual / hypothesis |
| Tire outer width with 260 mm tire: baseline / F14 | 1,704 / 2,100 mm | derived |
| Joint angle at ±80 mm vertical travel: baseline / F14 | 9.62° / 6.81° | F14 calculation, vertical-only motion |
| Engine reservation above the proposed floor (F14) | 10 mm | F14 trial |

Four options were offered: (1) widen the body and the track, (2) keep the 993
body width and move the engine, floor or shaft angle, (3) change the driveline
concept, (4) pause F15+ packaging until measured inputs exist.

## Decision

**Option 1.** F15+ packaging takes a widened body with a wide track as its
research target, with the track somewhere between the baseline and the F14
trial value. The 1,735 mm documentary body width no longer bounds the research
envelope; it stays recorded as the 993 baseline.

Nothing numeric is fixed by this decision. The F14 trial stays a hypothesis:
no track, body width, floor height or shaft geometry is selected, and the
10 mm engine reservation above the floor remains unresolved.

## Inputs this option needs (none is in the repository)

1. A widened-body surface source with a recorded licence; the only body
   surfaces are the documentary 993 envelope.
2. The engine output datum (bellhousing), measured separately from the scan's
   cylinder-row direction.
3. A manufacturer transaxle drawing and an accepted input-torque spectrum.
4. Measured suspension hardpoints, to replace the vertical-only wheel motion.
5. Masses and centres of gravity.
6. Tire limits for the chosen tire.

Under [decision 0019](0019-accept-contributed-measurements.md) items 2, 4 and
5 may come from outside contributors. Until they exist, any sweep of the wide
track is tuning on hypotheses, the same admissibility rule AGENTS.md states
for meshes.

## Consequences

- [INTEGRATION.md](../../twins/vehicle-911-917/INTEGRATION.md) records the
  direction and adds the widened-body source to its next work.
- Options 2 to 4 are not pursued for now; the option texts stay on #464.
- No chassis, suspension, driveline or engine component is released, and no
  attachment coordinate, material allowable or tire-friction value is
  supplied.
