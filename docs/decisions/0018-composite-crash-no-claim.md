# ADR 0018: no crashworthiness claim for the composite monocoque

## Status

**Proposed** on 2026-11-06 (issue #441). It becomes accepted when the owner
records acceptance on #441. Until then the position below already applies,
because it only restates the gates that [docs/SAFETY.md](../SAFETY.md) and
[the monocoque programme](../MONOCOQUE_964_993_PROGRAMME.md) (section 8) close
today.

## Context

The 964/993 carbon monocoque programme has stiffness and buckling models
(CalculiX shells, field-lattice studies, renders). The computation-chain note
[MONOCOQUE_964_993_COMPUTATION_CHAIN.md](../MONOCOQUE_964_993_COMPUTATION_CHAIN.md)
leaves the crash question open. It names OpenRadioss as the explicit solver for
designing energy-absorption zones, and it states that composite crash
behaviour (progressive crushing, delamination, fibre failure) cannot be predicted
without coupon and crush-tube calibration.

A monocoque carries occupant restraint anchorages, suspension pick-ups,
jacking points and primary fasteners. SAFETY.md presumes all of them critical.

## Decision

1. **Crash state, recorded explicitly:** `unvalidated`. Safety class of every
   monocoque geometry: `prohibited_pending_engineering`. There is no crash
   model, crash test, correlation or engineering review in the repository.
2. **No crash claim of any kind** (crashworthiness, energy absorption, cell
   integrity, occupant protection, "equivalent to" a steel shell) may appear in
   a record, page, render caption or report. The following never count towards
   one:
   - CalculiX stiffness or linear buckling results;
   - field-lattice, gyroid or topology studies;
   - renders, USD scenes or PicoGK geometry;
   - a hypothetical OpenRadioss or other explicit model that has not been
     calibrated and correlated against physical tests;
   - surrogate (PhysicsNeMo) predictions.
3. An explicit crash model may be built later **only as a design and
   comparison tool**, under the plan stub
   [MONOCOQUE_CRASH_VALIDATION_PLAN_STUB.md](../MONOCOQUE_CRASH_VALIDATION_PLAN_STUB.md).
   Its outputs stay labelled "uncorrelated design study".
4. Lifting any part of this position requires all three: an executable
   validation plan approved by a qualified engineering reviewer, physical test
   results from a facility selected by qualified professionals, and a signed
   review in the sense of SAFETY.md. Agent or model output can supply none of them.

## Consequences

- The M0 homologation route (#439) and the M1/M2 reference-body and torsion
  data (#440, #548, #549) come first. Without them no crash work has a defined
  structure, boundary or regulatory target.
- The stub lists questions, not answers. It sets no test method, standard,
  pulse, mass or acceptance value, because those belong to the qualified
  reviewer and the homologation route.
- Phase M7 of the programme (engineering review and physical test plan) is the
  earliest point where this ADR can be revisited.
