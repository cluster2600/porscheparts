# ADR 0021 — Engine carrier: Turbo variant chosen, V5 verdict recorded

## Status

Accepted by the project owner for
[issue #482](https://github.com/cluster2600/porscheparts/issues/482): chosen on
2026-11-05, confirmed on 2026-11-09. A draft of this record written on
2026-11-05 under the number 0018 was never published; 0018 has since been
used for the composite-crash decision, so this record takes 0021.

## Context

`993-ENG-CARRIER-0001` had three non-interchangeable PET candidates
(993 115 021 90 standard, -41 RS, -53 Turbo), a V5 Ti-6Al-4V bionic study at a
nominal 1.185 kg that fails the structural screen, an uncaptured OEM blade, and
an unsourced "45 to 50 Nm" figure presented beside the carrier torque.

## Decision

1. **Target variant: Turbo, 993 115 021 53.** Suffix 54 is recorded as the
   documented supersession lead (Sunset Porsche lists 54 as superseding 53);
   geometric equivalence between 53 and 54 is not established and must not be
   assumed.
2. **V5 verdict: fails the structural screen; blocked on measured interfaces.**
   V5 is kept as a concept study. It is neither withdrawn nor iterated further
   until measured interfaces exist.
3. **Torques.** Only 85 Nm on M12 (carrier to engine mount, group 10 factory
   table) is retained for this part. 46 Nm belongs to the gearbox mount to body
   shell. The unsourced 45 to 50 Nm figure is withdrawn as a carrier value.

## Where this decision is recorded

This record is the authoritative statement of the decision for now. The
catalogue record and the generated part page are deliberately **not** edited:

- `catalog/parts/993-eng-carrier-0001.json` is a registered input of the
  carrier gate: its SHA-256 is bound in `benchmarks/free-tools/baseline.json`,
  whose own SHA-256 is pinned by the frozen bionic-turbo baseline
  (`twins/bionic-turbo-f1/baseline-20261106*/runtime-matrix.json`).
- `scripts/templates/carrier-study.md.in`, which generates the part page, is
  pinned by `containers/stack-20261105/recon-native-validation.json`.

AGENTS.md forbids editing a file whose SHA-256 is pinned by a lock or an
evidence contract, so the record and the page take up this decision at the
next re-registration of the carrier inputs, in a new generation rather than by
rewriting the pinned files. Until then, nothing in them contradicts this
decision: the record already says the 45 to 50 Nm figure is absent from the
factory table and that the three carriers are not interchangeable.

## Consequences

- The catalogue status stays `concept`; no fitment, strength, fatigue or
  manufacturing claim follows from this decision.
- Blade capture remains blocked: no part is available to this project. Since
  [decision 0019](0019-accept-contributed-measurements.md) a measurement
  contributed by an outside contributor is admissible, but none has been
  received. Issue #482 stays open for the capture.
- Release still requires documented professional engineering review and an
  approved validation plan (SAFETY.md).
