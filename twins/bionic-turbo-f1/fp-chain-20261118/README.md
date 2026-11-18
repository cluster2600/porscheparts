# Conversion chain and native floating point — 18 November 2026

Additive revision for [issue #397](https://github.com/cluster2600/porscheparts/issues/397),
gate `G04-native-fp-execution`. It follows the
[interface ledger and comparison basis](../basis-20261112/README.md) and changes
no earlier revision directory and nothing under `evidence/`. The owner asked on
2026-11-18 to continue the roadmap as a **provisional synthetic comparison**:
nothing here concerns a physical turbocharger.

**Result: the gate is `investigated`, not passed.** The conversion chain is
prescribed, the pinned runtime is identified byte for byte, and two readers
agree on every conversion and bound. The unchanged evaluator still refuses G04
for five named blockers: the pinned linux/arm64 binary has not been executed,
the native non-orthogonality threshold (a libm cosine with no verified error
bound) is unresolved, no admissible native input exists, the sensitivity and
conditioning of the native criteria are not certified, and the compiler and
its options are not recorded in the binary.

No OpenFOAM process, mesher, solver, container or remote host was run. One
image was pulled by digest and read statically. The recurring turbo automation
stays paused. Case 084, the PR229 `blockMeshDict` and the PR238–256 traversals
were not touched. All 153 boxes and the two undecided determinants are kept.

## What this revision contains

| File | Content |
|---|---|
| [PLAN.md](PLAN.md) | Method, acceptance criteria and limits, committed alone before application (e68d171c) |
| [conversion-contract.json](conversion-contract.json) | The prescription: stages, bounds, branches, budgets, operation model, rules, witnesses, reference cells |
| [contract-amendment-20261118.json](contract-amendment-20261118.json) | Dated amendment after review: the libm cosine threshold is unresolved, not bracketed |
| [readback_image.py](readback_image.py) | Static reader of the pinned image (no container, nothing executed) |
| [runtime-readback-20261118.json](runtime-readback-20261118.json) | Its receipt: digests, hashes, ELF facts, constants, fused instructions |
| [fpchain.py](fpchain.py) | Primary reader and checker |
| [conversion-receipt.json](conversion-receipt.json) | Primary receipt: witnesses, thresholds, certificates, margins, reference cells |
| [independent_reader.py](independent_reader.py) | Independent reader (integer IEEE emulation; does not import the primary) |
| [independent-readback.json](independent-readback.json) | Its verdict: 1662 comparisons, no mismatch |
| [gate-ledger.json](gate-ledger.json) | Ledger revision: only G04 changes |
| [G04-attestation.json](G04-attestation.json), [G04-evaluation.json](G04-evaluation.json) | What was submitted to the unchanged evaluator, and its verdict |
| [prerequisites.json](prerequisites.json) | Gate-level confirmation of #394 and #395 |
| [host-observations-20261118.json](host-observations-20261118.json) | What ran on the host, and the steps skipped |

## Prerequisites

G04 depends on G01 and G02, not on G03. The unchanged
[`baseline.py`](../baseline-20261106/baseline.py) still accepts the recorded
attestations of `G01-baseline-frozen`, `G01-execution-contract` and
`G02-evidence-recoverable`; [prerequisites.json](prerequisites.json) keeps
that evaluation and `fpchain.py check` repeats it. G03 stays `investigated`.

## Three source facts that shape the chain

Read from the pinned official archive `OpenFOAM-v2406.tgz` (`8d1450fb…`),
taken from the project's own release and checked against its receipt:

1. **The reader rounds twice.** `doubleScalar.C` parses with `::strtold`. On
   linux/arm64 `long double` is IEEE binary128, so a text is rounded to 113
   bits and then narrowed to binary64. That is not one correctly rounded
   conversion.
2. **Tiny values become zero.** `Scalar.C` returns `+0` for every parsed value
   with `-VSMALL <= q <= VSMALL` (sign lost) and refuses `|q| > VGREAT`.
3. **The compiler may fuse.** The `linuxARM64Gcc` rules compile with
   `g++ -std=c++14 -O3` and no `-ffp-contract`, which allows fused
   multiply-add on aarch64.

## The prescribed chain

| Stage | From → to | Rule | Error bound |
|---|---|---|---|
| S1 | exact rational → text | 16 significant digits from the exact rational, ties to even, `%.16g` style | ½·10^(E−15), at most 5·10⁻¹⁶ relative |
| S2 | text → binary64 | native: label token, or binary128 then binary64; zero branch; range refusal | 2⁻⁵³ + 2⁻¹¹¹ relative outside the zero branch |
| S3 | binary64 → text | native write at writePrecision 16, correctly rounded, ties to even | 5·10⁻¹⁶ relative |
| S4 | text → binary64 | S2 again | as S2 |

One read costs at most β ≈ 6.11·10⁻¹⁶ relative; the budget allows one native
rewrite, (1+β)² − 1 ≈ 1.22·10⁻¹⁵. A **double-rounding lemma** shows that the
two roundings of S2 agree with one correct rounding for any 16-digit text with
|x| ≥ 10⁻¹⁰. Smaller non-zero coordinates must be checked one by one.

The operation bounds count roundings on the unfused evaluation, so they hold
for every pattern of fused multiply-add. Reassociation is not covered. Two
exact facts matter. The vector area of a face, ½ Σ pᵢ × pᵢ₊₁, does not depend
on the fan centre. The area vectors of a closed cell or a closed boundary sum
to exactly zero. Neither is true of the computed values. A comparison with a
threshold is **decided** only when the whole interval of its possible computed
values lies on one side. Otherwise it is **undecided** and kept, never
resolved by choosing a point.

## The pinned runtime, read statically

The image `opencfd/openfoam-run@sha256:1db0df06…` was pulled by digest and
exported with `docker save`. Its layers were then read in Python; no container
was created. [The receipt](runtime-readback-20261118.json) shows:

- The manifest digest and the linux/arm64 platform match the runtime matrix
  row `opencfd-v2406-runtime`. So do all five pinned executables, `checkMesh`
  included: `469fa2e3…`.
- `libOpenFOAM.so` imports `strtold`, `__trunctfdf2`, `__letf2` and
  `__getf2`. The binary128 path of S2 is present in the binary, not only in
  the source.
- Nine exported constants equal the binary64 roundings of their source
  literals bit for bit. They are `VSMALL`, `VGREAT`, `ROOTVGREAT`, and the mesh
  thresholds `closedThreshold`, `aspectThreshold`, `nonOrthThreshold`,
  `skewThreshold` and `planarCosAngle`.
- The geometry functions take `Vector<double>` and `UList<int>`, so scalar is
  binary64 and label is 32-bit.
- The image's own `META-INFO/manifest.txt` is byte-identical to the one
  archived from the Mac on 2026-10-12. The git blob ids it lists for the 13
  source members read equal those of the pinned archive.
- The geometry functions contain **76 fused multiply-add instructions**,
  including 11 in `makeFaceCentresAndAreas` and 16 in
  `makeCellCentresAndVols`. Native results therefore need not equal any
  unfused re-evaluation; they can only be bounded.
- The image runs Ubuntu 24.04, glibc 2.39-0ubuntu8.2, libstdc++
  14-20240412 and package openfoam2406 2406.0-1. There is no `fesetround` or
  `fesetenv` import and no `MSR FPCR` instruction in `checkMesh` or
  `libOpenFOAM.so`.
- The binaries carry **no compiler string** and no recorded options.

## What the readers found

The primary and the independent reader agree on 1662 comparisons. All 17
rational and 13 text witnesses stay within their bounds. They exhibit all 15
witness classes of the contract:

- `VSMALL` itself (1.0000000000000000250·10⁻³⁰⁰) is written `1e-300` at
  writePrecision 16 and **read back as 0**. Writing it with 17 digits gives
  the same text.
- 0.1 + 0.2 is written `0.3` and read back as a different binary64 value.
  2⁵³ + 1 is read as 2⁵³ and written back as a different text. Sixteen digits
  give neither round trip.
- The 37-digit text `1.000000000000000111022302462515654043` is read natively
  as 1. Its correct rounding is 1 + 2⁻⁵². This is a witness of double
  rounding outside the lemma.
- `-0` and `-0.0` are read as `+0`; text below `VSMALL` reads as zero; a token
  of 128 characters is refused.

On 62 synthetic reference faces (offset, rotated and warped hexahedra, a
prism, a 2×2×2 block and three tiny squares; none is turbo geometry), every
unfused and fused result lies within its bound. Fused and unfused results
differ in 86 face–pattern cases. The closed-cell sums are zero exactly but not
in binary64: 45 of 48 cell sums and 18 of 20 boundary sums are non-zero. All
stay within bound and are decided closed. The three guard squares are decided
active, undecided and inactive. The undecided one is kept as it is.

## Certified margins and what they do not decide

Read exactly from the pinned certificates:

| Criterion | Certified bound | Native threshold | Margin |
|---|---:|---:|---:|
| Flatness | ≥ 0.85458 | 0.8 | 5.46·10⁻² |
| Non-orthogonality (cosine) | ≥ 0.3420216 | unresolved (libm `cos`, no verified bound) | none; 1.44·10⁻⁶ only if `cos` were faithfully rounded |
| Skewness | ≤ 3.98492 | 4 | 1.51·10⁻² |
| Interpolation weight | ≥ 0.0501409 | 0.05 | 1.41·10⁻⁴ |
| Volume ratio | ≥ 0.30146 | 0.01 | 0.291 |

These are mathematical margins of the certified representation. Each is many
orders of magnitude above a rounding error. Even so, deciding a native
comparison needs a bound on how far the criterion moves with the conversion
displacement, and how ill-conditioned its formula is over the 153 boxes. No
certificate provides either, so **no native criterion is decided** here.

The face guard is the exception. Twice the smallest certified face area bounds
the fan sum from below. The guard `sumA < ROOTVSMALL` is therefore inactive
for every quad of a written input whose coordinates satisfy
|x| ≤ 372.6 length units. That bound can be checked directly on any future
input.

**The non-orthogonality threshold is unresolved.** OpenFOAM computes it as
`::cos(degToRad(70))` with the image's glibc 2.39. glibc does not promise
correctly rounded `cos`, and its published error figures are test
measurements, not proofs. No verified error bound for that implementation is
held here, and the binary was not executed, so the value it returns is not
established. The two binary64 neighbours of the exact cosine of the binary64
argument are recorded only as a conditional figure, valid if `cos` were
faithfully rounded. The [dated amendment](contract-amendment-20261118.json)
withdraws the contract's earlier wording, which treated that bracket as the
native threshold; the contract file itself is unchanged.

**A conditional finding for the inherited packages.** The 2026-10-13
orthogonality package used a threshold interval around the mathematical
cos(70°). Both binary64 neighbours of the exact cosine of `70·π/180` lie above
that interval, by 1.64 and 2.64 units in the last place. If the pinned `cos`
is faithfully rounded, the inherited interval therefore does not contain the
native threshold. Whether it is, is part of the same open question.

## Gate state

The [ledger revision](gate-ledger.json) inherits the opening rule, the
comparison contract and every other gate unchanged. G04 moves from
`not_started` to `investigated`. It gains six configuration pins, the
amendment among them, and five receipts. Its blocker
`conversion-chain-not-prescribed` is recorded as resolved, with its receipts.
Five precise blockers remain:

1. `pinned-binary-not-executed`
2. `native-nonorthogonality-threshold-unresolved`
3. `no-admissible-native-input`
4. `criterion-sensitivity-and-conditioning-not-certified`
5. `compiler-and-options-not-pinned`

The [attestation](G04-attestation.json) carries the runtime identity read from
the image: variant, version, linux/arm64, image digest and `checkMesh` hash.
Every binding and every pin is accepted. The unchanged evaluator
[refuses](G04-evaluation.json) the gate for exactly the five blockers and
nothing else. G05 stays closed behind G03 and G04.

## Not done, and why

- **Execution of the pinned binary.** This host is x86_64 with no arm64
  executor. Its amd64 sibling image is a different runtime row, and
  substituting it is prohibited. No emulator was installed. Remote hosts were
  excluded today.
- **Native decisions for the turbo representation.** They need sensitivity and
  conditioning certificates. Deriving those is new work that must reuse, not
  replay, the earlier traversals.
- **Compiler pin.** Nothing in the binaries records it.
- **The libm cosine.** No proven error bound for glibc 2.39 aarch64 `cos` is
  available, so the threshold it produces is left unresolved.
- **A native input.** None exists. Selecting a point, a ratio or a candidate
  to make a check pass is refused. The contract documents how a later input
  could be admitted.

## Verify

```sh
python3 twins/bionic-turbo-f1/fp-chain-20261118/fpchain.py check
python3 twins/bionic-turbo-f1/fp-chain-20261118/fpchain.py gate
python3 twins/bionic-turbo-f1/fp-chain-20261118/independent_reader.py
python3 -m unittest tests.test_bionic_turbo_fp_chain
```

`check` exits 0 on the committed files. It recomputes everything that needs no
private input. `gate` exits 1 and prints the five refusals: that is the
recorded verdict, not a fault. The `apply` command of `fpchain.py` and
`readback_image.py` need the private archive and image export. Their outputs
are the committed receipts.

## Next permitted action

Each of these must be prescribed before it is applied:

1. An owner decision on an arm64 host (the Mac) for a synthetic native probe:
   the frozen witness texts and reference cells only, run by the pinned image
   with its hashes verified at launch. It would also observe the native
   non-orthogonality threshold, unless a proven error bound for the pinned
   `cos` is found first.
2. A documentary search for the build recipe of openfoam2406 2406.0-1 arm64.
3. A derivation of sensitivity and conditioning bounds that reuses the pinned
   certificates without replaying their traversals.

None of them selects a native input, launches a solver, or touches case 084 or
the PR229 `blockMeshDict`.
