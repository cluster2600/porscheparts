# Prescribed native scalar controls

The hash-verified v2406 sources show `ISstream.C:782` calling the bool
`readScalar` overload. Under WM_DP that dispatches to `readDouble`; its
implementation substitutes `strtold` and uses the inclusive VSMALL zero guard
in `Scalar.C:98-117`. This differs from both `ISstream::read(double&)` and the
strict guard in the value-returning string overload. Do not substitute them.

Run only the following synthetic single-entry inputs, each in its own private
file, with the pinned image's `foamDictionary -disableFunctionEntries
-precision 16 -entry value -value`. Use its standard bashrc, locale C, no
network, read-only root and input mount, non-root UID, 256 MiB, one CPU and
64 processes. Maximum 20 seconds per input and 120 seconds overall. No mesh,
case, include, function entry or source program is loaded.

| ID | Input text | Predeclared observation criterion |
|---|---|---|
| zero | `0.0` | accepted zero |
| negative-zero | `-0.0` | accepted positive zero spelling after zero guard |
| subnormal | `4.9406564584124654e-324` | accepted zero, not retained binary64 subnormal |
| tiny-normal | `1e-308` | accepted zero despite being representable as binary64 |
| below-small | `9.99999999999999e-301` | accepted zero |
| decimal-small | `1e-300` | record boundary result without assuming equality to the binary constant |
| above-small | `1.000000000000001e-300` | accepted positive nonzero |
| negative-tiny | `-1e-308` | accepted zero |
| ordinary | `1.2345678901234567` | accepted; record loss at precision 16, no exact-round-trip claim |
| integer-over-label | `9007199254740993` | accepted scalar; record representational loss |
| range-overflow | `1e301` | rejected token, nonzero exit |

Keep every stdout/stderr and exit code. Independently parse output decimals as
exact rational numbers, without the native runner or binary float conversion.
For the two ordinary finite outputs, compare absolute error to the conservative
bound `abs(input) * 1e-15`; this is a prescribed control threshold, not a proof
of the full formatting algorithm or libm. Preserve the boundary observation as
unqualified. Mutated controls must be rejected by the independent reader.

Record all source member hashes and the actual utility hash. These controls
cover one token-read/output path only. Compiler flags, rounding modes, branch
bounds for geometry and accumulation budgets remain unresolved; G04 cannot pass.
