# ADR 0019: accept measurements contributed by outside contributors

## Status

**Accepted** on 2026-11-06 by the project owner, on issue #437 ("i accept
others measurements": option B of the options posted there). It amends the
operating constraint of [PROJECT_CHARTER.md](../PROJECT_CHARTER.md) and
[decision 0013](0013-pilots-advance-on-documentary-evidence.md). It does not
replace them.

## Context

Since 2026-09-14 the charter has said that nothing is bought, weighed, measured,
printed, fitted or tested, by the maintainer or the owner. It also said that a
dimension no document gives is "never assigned to someone to measure". Records
cap at `concept`, and the exit criteria of phases 2 and 3 have waited on an
outside contributor that the frame did not let the project ask for. 25 open
issues are labelled `measurement`.

The options were:
- **A**, stay digital-only;
- **B**, accept contributed evidence under conditions, still buying and
  measuring nothing in-house;
- **C**, B plus owner-funded measurement.

The owner chose **B**.

## Decision

1. **Unchanged:** the maintainer and the owner buy no part, and weigh, measure,
   print, fit or test nothing themselves. Nobody is paid or commissioned to
   measure.
2. **New:** the repository may **request** a measurement, photo, scan or fit
   report from an outside contributor, through a published measurement plan or
   issue, and may **accept** what a contributor sends in, under these conditions:
   - **Method:** the contribution comes through the
     [capture protocol](../CAPTURE_PROTOCOL.md) and its tools
     (`scripts/capture_caliper.py`, `scripts/capture_photoset.py`), with
     instrument, uncertainty, repeats, datums and method declared. A bare
     figure is not admitted.
   - **Rights:** the contributor grants an explicit licence (for example
     CC-BY-4.0 for measurements and photos). It is recorded in a source record
     before the data is used. Without a grant, the contribution is not used.
   - **Privacy:** no VIN, owner name, address or other personal data enters
     Git. The specimen gets an anonymous ID, and raw photos, scans and
     correspondence stay in private storage with their hashes.
   - **Review:** each contribution is checked independently of its contributor
     (record validators, plus a second reader for interface dimensions). A
     contributor's data is never its own inspection evidence, and model output
     can't review it either.
   - **Same specimen:** host and part readings used together must come from an
     identified specimen and say whether they share one.
3. **Status consequences:**
   - `dimensionally_reviewed` becomes reachable for a record whose dimensions
     come from an admitted contribution.
   - `prototype_fitted` becomes reachable only with a contributor's fit report
     that names its specimen.
   - A twin may reach `F2_interface` only from admitted measurements of the
     interfaces themselves.
4. **Safety is unchanged.** [SAFETY.md](../SAFETY.md) classes and the
   engineering-review rule still apply. Contributed data never releases a
   braking, steering, suspension, restraint, fuel-system, wheel or highly
   loaded engine part, and it is never a crash or structural claim
   (see ADR 0018 for the monocoque).

## Consequences

- Phase 2 resumes for the three pilots (switch blank, seat rail cover, door
  pull). [MEASUREMENT_CAMPAIGN.md](../MEASUREMENT_CAMPAIGN.md) becomes the
  public request to contributors.
- The `measurement` issues are no longer blocked by the frame itself. They
  stay `external-blocked` until a contribution arrives, and each is closed only
  by admitted data.
- Option C (owner-funded measurement) stays out of scope until the owner
  decides otherwise.
