# Native scalar-path evidence for #397

The pinned OpenCFD 2406 utility passed **13 prescribed scalar controls** and
an independent exact-rational readback. Two results matter for the remaining
execution proof:

- The token parser maps a true normal binary64 magnitude, `1e-305`, to zero.
  Its source guard uses VSMALL, not the smallest representable binary64 value.
- The exactly representable input `1 + 2^-52` is written as `1` at precision
  16. The exact difference is `1/4503599627370496`. Precision 16 therefore
  cannot be assumed to preserve every binary64 value through text.

**G04 remains unqualified.** These are bounded controls of one token input and
output route. They do not bound native geometry operations, qualify all stream
overloads, prove the actual build flags or rounding environment, or admit a
mesh or solver. No geometry, old proof traversal or solver was executed.

## Source and runtime bindings

The [recovery receipt](source-recovery.json) records 26 independently rehashed
files from the historical native-admission dossier. The additional official
52,374,726-byte OpenFOAM archive matches its historical SHA-256. The
[source bindings](source-bindings.json) identify the exact members and lines.
All source archives and extracted files remain private; none is imported into
Git or executed.

`ISstream.C:782` uses the bool `readScalar` overload. Under WM_DP it dispatches
to `readDouble`, which substitutes `strtold` into `Scalar.C`. That bool overload
maps values inside the **inclusive** VSMALL interval to zero. The value-returning
string overload has a strict guard, and `ISstream::read(double&)` uses a C++
stream directly. These paths must not be treated as interchangeable.

`OSstream::write(double)` delegates to its C++ stream; its precision setting
also delegates. The published ARM64 GCC optimization rule includes `-O3` and
declares a rounding-math variable, but published defaults do not prove the
options used for the installed binary.

The [runtime preflight](runtime-preflight.json) records build
`_be01ca78-20240625`, `LSB;label=32;scalar=64`, installed package versions and
22 resolved library hashes. The loader and vDSO are excluded from that list.
Compiler flags, effective rounding mode and libm bounds remain unknown.
Configuration labels DP/Gcc/Opt are recorded as configuration only.

## Trials and independent checks

The [initial scalar plan](SCALAR-PLAN.md) and [cases](scalar-cases.json) were
fixed before execution. The [first attempt](scalar-first-attempt.json) is
rejected: passing the input filename through bashrc's positional arguments
caused an attempted shell sourcing of data and `value: command not found`.
The [declared retry](SCALAR-RETRY.md) clears that argument before setup;
criteria and inputs remain unchanged. Unexpected setup diagnostics are rejected
by the independent reader.

The [corrected native receipt](native-scalar-receipt.json) and
[independent readback](independent-scalar-receipt.json) cover eleven inputs.
The historical case ID `tiny-normal` contains `1e-308`, which is subnormal;
that ID is retained and is not evidence for a normal-value test.
The [supplemental plan](SUPPLEMENT-PLAN.md), [two inputs](supplement-cases.json),
[native receipt](supplement-native-receipt.json) and
[independent readback](supplement-independent-receipt.json) supply the true
normal and exact binary64 controls described above.

| Observation | Result |
|---|---|
| Zero, negative zero and subnormal inputs | Printed `0`; negative-zero spelling is lost on this path. |
| Normal `1e-305` | Printed `0`. |
| Decimal `1e-300` | Printed `0`; exact threshold equality remains an observation, not a universal boundary proof. |
| `1.000000000000001e-300` | Survives as positive nonzero. |
| `1.2345678901234567` | Printed `1.234567890123457`; decimal text changes. |
| `9007199254740993` | Printed `9007199254740992`. |
| Exact binary64 `1 + 2^-52` | Printed `1` at precision 16. |
| `1e301` | Native fatal IO rejection, exit 1. |

The [independent reader](verify_scalars.py) parses decimals as `Fraction`, never
as binary floats, and imports no native runner. Its finite error threshold is
a prescribed control tolerance, not a derived bound for the whole algorithm.
The four focused tests also reject missing/duplicate controls, changed inputs,
precision substitution, unexpected warnings, nonzero tiny results and a false
overflow success. They verify all source, plan, reader and receipt hashes.

Recheck the saved native observations without rerunning a native utility:

```sh
python twins/bionic-turbo-f1/fp-contract-20261106/verify_scalars.py
python -m unittest discover -s tests -p test_bionic_turbo_fp_contract.py -v
```

To reproduce native controls, use the exact image, utility hash, resource limits
and corrected launcher recorded in the native receipt. Create new private
single-entry input files from the prescribed cases; mount them read-only at
`/controls`. The launcher uses `-disableFunctionEntries -precision 16 -entry
value -value`. Never pass data filenames as arguments to the sourced bashrc.

## Remaining obligations

Bind the actual compiler options and effective arithmetic environment to the
binary, then prescribe per-operation bounds, native guard intervals, closure
accumulation budgets and an independent reader over the inherited certificates.
Include this token parser's zero guard and long-double intermediate explicitly;
a generic binary64 conversion model is insufficient. Preserve all 153 closed
boxes and both undecided determinants. No arbitrary ratio, candidate, mesh,
threshold relaxation, PR229 dictionary or case 084 is introduced here.
