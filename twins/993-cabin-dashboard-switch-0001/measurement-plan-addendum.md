# Measurement plan addendum: corner compatibility (H04)

This addendum extends [the twin measurement plan](evidence/measurement-plan.md),
which is frozen under `evidence/` and is not edited. It adds one part-side
input and makes the host corner reading precise, so that
[`source/check_fit.py`](source/check_fit.py) can evaluate the corner rule of
[the interface contract](interface-contract.json). It records which readings
are required; it holds no value.

## Why a part-side input is needed

H04, the inner corner radius of the opening, can only be judged against the
corner of the body that passes through it. D04 in
[the part measurement plan](../../parts/993-int-switch-blank-0001/evidence/measurement-plan.md)
is the corner radius of the visible face, which stays in front of the panel. It
is a different feature and cannot stand in for the body corner. No radius is
assumed for it.

## Added and clarified readings

| ID | Feature | Method | Repeats |
|---|---|---|---:|
| D10 | smallest outer corner radius, in plan view, of the four corners of the insertion body, in the section measured by D08 and D09, clips excluded | radius gauge | 3 |
| H04 | largest inner corner radius, in plan view, of the four corners of the empty opening, in the narrowest section, the one measured by H01 and H02 | radius gauge | 3 |

Inspect all four corners of each feature and record the extreme one: the
largest opening corner and the smallest body corner are the conservative pair.
Take H04 on the empty opening; a radius deduced from the removed part is
refused.

## Evidence the record cannot carry

The rule assumes each corner is a circular arc tangent to both adjacent sides.
A chamfered, notched or non-tangent corner falls outside it. Add one photograph
per corner of the opening and of the insertion body with the gauge leaf in
contact, labelled with the same `D10`/`H04` identifiers.

## Rule

With the body centred in the opening, `c_x = (H01 - D08) / 2`,
`c_y = (H02 - D09) / 2` and `delta = H04 - D10`, the smallest all-round gap is
`delta - hypot(c_x - delta, c_y - delta)` when both `c_x` and `c_y` are below
`delta`, and `min(c_x, c_y)` otherwise. The worst case uses the smallest
opening, the largest body, the largest H04 and the smallest D10 inside their
uncertainties. A pass requires a positive worst-case gap. The derivation and
preconditions are in [the interface contract](interface-contract.json).

A positive gap is a static geometric result. It does not predict clip
insertion or retention force, and it does not establish a fit.
