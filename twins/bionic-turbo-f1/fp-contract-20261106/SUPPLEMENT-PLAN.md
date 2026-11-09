# Two supplemental scalar controls, prescribed before execution

The existing ID `tiny-normal` contains `1e-308`, which is actually subnormal
for binary64. Preserve that original ID and receipt; do not use it as evidence
about normal values. Add `small-normal = 1e-305`, a normal binary64 magnitude
below VSMALL, with the predeclared result zero.

Add `exact-binary64 =
1.0000000000000002220446049250313080847263336181640625`, exactly `1 + 2^-52`.
This rational is itself a representable binary64 value. At precision 16 the
predeclared output is `1`, differing by exactly `2^-52`; it is a direct control
against assuming an exact write/read round trip. Independently compare the
decimal rationals, with no binary float conversion.

Use the corrected launcher, identical runtime and disabled function entries,
new private inputs, and the original per-command limits. Execute no original
controls again. Hash this plan, both inputs and the native receipt. The existing
independent reader is unchanged; retain its generic error bound and additionally
check the exact supplemental expectations. G04 still cannot pass.
