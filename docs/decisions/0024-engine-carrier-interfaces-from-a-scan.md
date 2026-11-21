# ADR 0024 — Engine carrier: a contributed scan may establish its interfaces

## Status

**Accepted** by the project owner on 2026-11-20, in a working session, by
answering "yes" to the question whether the carrier plan should accept a scan,
with a few contact measurements kept as a check. It applies to
`993-ENG-CARRIER-0001`, the Turbo carrier 993 115 021 53 chosen in
[decision 0021](0021-engine-carrier-turbo-variant-and-v5-verdict.md), and to
nothing else.

It amends, for this part only, the rule of the carrier's
[measurement plan](../../parts/993-eng-carrier-0001/evidence/measurement-plan.md)
("the scan does not fix the interfaces: D01 to D07 stay measured by contact")
and the rule of the [capture protocol](../CAPTURE_PROTOCOL.md) that interface
dimensions come from the caliper. The plan is an evidence file and is not
edited; this record is where the change is stated.

## Context

The carrier has been blocked on its interfaces since
[issue #482](https://github.com/cluster2600/porscheparts/issues/482): the four
central attachment centres, the two end axes, the mating faces, and the blade
profile and thickness have never been measured. The published request asks
contributors for three caliper readings and a photograph. None has arrived.

Two things changed in November 2026:

- On 2026-11-19 the project rules began to accept a 3D scan of the physical
  part as an independent reference for a model's accuracy, provided the scan is
  named and the deviation is reported ([CLAUDE.md](../../CLAUDE.md)).
- The 935 head twin now holds a working chain from a scan to checked features.
  Each feature is fitted on half the scan's vertices and checked on the other
  half by CloudCompare, against an acceptance written down before the first run
  ([feature checks](../../twins/935-cylinder-head-cad-twin/params/feature-check.json)).
  The first 32 fits gave 4 confirmed features, and the others are recorded as
  unconfirmed rather than adjusted. That head scan was a found scan with no
  scale bar, so its features establish no dimension of the specimen. Here the
  scale bar and the caliper checks below supply what that scan lacked.

A scan of the carrier captures every interface in one session: the hole
positions, the axes, the faces and the blade. With contact measurement, each of
those needs its own instrument and datum.

## Decision

1. **A scan may establish the interfaces.** A 3D scan of an identified
   specimen of 993 115 021 53 may supply D01 to D07 of the measurement plan, the
   four central and two end attachment axes, the mating faces, and the blade's
   profile and thickness. It must be contributed and admitted under
   [decision 0019](0019-accept-contributed-measurements.md): the capture
   protocol, an explicit licence, an anonymous specimen ID, and the raw scan
   kept in private storage with its SHA-256.
2. **Contact measurements stay, as checks.** The same specimen must also have
   at least three caliper readings, with three repeats each. None of them is
   used to scale or register the scan:
   - D03, the diameter of a body-mounting hole;
   - D05, the diameter of an engine-mount hole;
   - D07, the material thickness at an attachment.

   The scale comes from a certified scale bar in the field (P3 of the
   protocol). Without one, D01 is measured by contact and used for scaling, and
   the record says so.
3. **Thresholds before acquisition.** Before any scan is taken, a commit
   records each check dimension, its threshold `T` and what a failure means
   (P5). `T` is at least twice the caliper uncertainty of that dimension.
   Proposed values, to be accepted or changed in that commit:

   | Check | Proposed `T` |
   |---|---|
   | D03 and D05, hole diameters | 0.2 mm |
   | D07, thickness at an attachment | 0.2 mm |
   | D01 when it is a check (scale bar in the field) | 1.0 mm, twice a 0.5 mm rule |

   Deviation is scan minus caliper. Each check is `pass`, `fail` or
   `not_observable` (P5c).

   The owner accepted these values unchanged on 2026-11-21. They are committed,
   with the measurand of each check, the uncertainty rule and the verdict rule,
   in [the carrier's scan-check thresholds](../../parts/993-eng-carrier-0001/scan-checks/thresholds.json),
   before any scan or reply exists.
4. **Every feature is fitted on half the scan and checked on the other
   half.** A hole axis comes from its bore wall, or from its edge circles on
   both faces. A face is a plane fit, and the blade thickness is measured
   between its two fitted faces. The acceptance is the one the 935 twin uses,
   committed before any fit: at least 90 % of the held-out vertices within
   0.2 mm of the fitted surface, counting only vertices within 0.5 mm of it, and
   at least 100 of them. A feature that fails stays unconfirmed. A feature the
   scanner did not see stays null with the reason; nothing is filled from a
   photograph, the PET drawing or a neighbouring feature.
5. **If any check fails, the scan does not establish the interfaces.** The
   failure is recorded as a contradiction, and D01 to D07 fall back to the
   plan's contact rule. Nothing is rescaled, re-registered or dropped after the
   results are seen.
6. **What a scan never establishes:** material, heat treatment, the inside of
   a weld, thread form or class, coating thickness (unless it is measured or
   bounded), clamp and fit behaviour, loads, strength or fatigue. A scanner's
   point spacing is not its accuracy: the record states the scanner's model,
   settings and stated accuracy, and the check deviations measure it.

## Unchanged

- Who measures: the maintainer and the owner still measure and scan nothing
  themselves, and nobody is paid or commissioned to (decision 0019).
- Safety: the carrier is a highly loaded engine support. Admitted interfaces
  can make `dimensionally_reviewed` and `F2_interface` reachable under decision
  0019, with a second reader of the interface dimensions. They release nothing.
  A structural verdict still needs the load cases, a converged analysis, and
  documented professional engineering review with an approved validation plan
  ([SAFETY.md](../SAFETY.md)).
- Decision 0021 stands. V5 stays a concept study that fails the structural
  screen and waits on measured interfaces.

## Consequences

- The [measurement campaign](../MEASUREMENT_CAMPAIGN.md) lists the carrier with
  the scan route. The forum request filed in the part's evidence folder is not
  edited. A new request may say that a scan with a scale bar and three caliper
  readings is welcome.
- Once a scan is admitted, the interface capture runs with tools already in
  the repository: alignment with open3d and trimesh, features fitted by the
  [primitive fitter](../../benchmarks/scan-primitive-fitting/primitive_fit.py)
  on half the scan, and the held-out check against the other half with
  CloudCompare, as on the 935 head.
- Issue #482 stays open until a scan or a contact measurement is admitted.
