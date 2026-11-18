# Conversion chain and native floating point — method fixed before application

Issue #397, gate `G04-native-fp-execution`. Owner instruction of 2026-11-18:
continue the roadmap as a **provisional synthetic comparison**. Nothing here
concerns a physical turbocharger.

This plan and [conversion-contract.json](conversion-contract.json) are
committed **before** any pull, readback or reader run, in a commit of their
own. The application commits come after it. Every criterion below is enforced
by `fpchain.py check` and by `tests/test_bionic_turbo_fp_chain.py`.

## Read before writing this plan

- `next-scope.md` of the 2026-10-14 contact package, the native admission
  dossier, the checkFaceTets audit and the five native bound packages
  (flatness, orthogonality, skewness, weights, volume ratio).
- The pinned official archive `OpenFOAM-v2406.tgz`
  (`8d1450fb…a4686a`), read from the project's own release
  `bionic-turbo-native-binary-2026-10-12`, whose outer archive digest
  `87d6f62f…7a7558` matches its committed receipt. Members read: `Scalar.C`,
  `doubleScalar.C/.H`, `scalar.H`, `ISstream.C`, `OSstream.C`, `IOstream.H`,
  `TimeIO.C`, `primitiveMeshTools.C`, `primitiveMeshCheck.C`,
  `checkGeometry.C`, `sigFpe.C`, `etc/bashrc`, `etc/config.sh/settings` and the
  `linuxARM64Gcc` and `General/Gcc` wmake rules.

Three source facts shape the contract and were not in the earlier packages:

1. `doubleScalar.C` defines `ScalarConvert` as `::strtold`. The ASCII reader
   parses into `long double` and then narrows to `double`. On linux/arm64
   `long double` is IEEE binary128, so reading is a **double rounding**
   (decimal → binary128 → binary64), not one correctly rounded conversion.
2. `Scalar.C` rounds every parsed value with `-VSMALL <= q <= VSMALL` to
   `+0` (sign lost), and refuses `|q| > VGREAT`. The comparison is made in
   `long double` against the binary64 constant.
3. The `linuxARM64Gcc` rules compile with `g++ -std=c++14 -O3` and no
   `-ffp-contract` option. GCC's C++ default then allows fused multiply-add
   on aarch64. Native results need not equal any unfused evaluation.

## Scope and resource limits

- The work runs on the WSL host (x86_64, 25 GiB, 22 cores, shared). No
  remote host, no SSH, no paid compute.
- **Runtime pin.** Pull the pinned image
  `docker.io/opencfd/openfoam-run@sha256:1db0df06…0887532`
  (linux/arm64) by digest, export it with `docker save` to a private file
  outside Git, and read it statically. **No container is created or run**,
  nothing is executed from the image, and nothing is deleted. The amd64
  sibling already on the host is a different runtime row: it is not run.
  No emulator is installed or used.
- Python readers only, with the CI venv; each step under 30 minutes and
  under 8 GiB. No file over 1 MiB enters Git; extracted binaries and the
  image export stay in the private scratch directory and only their hashes
  are committed.
- No mesher, no solver, no OpenFOAM process, no case. The PR229
  `blockMeshDict` is not opened; case 084 is not touched; no PR238–256
  traversal and no earlier criterion is replayed. The recurring turbo
  automation stays paused. Nothing under `evidence/**` and no earlier revision
  directory is edited.

## Method

1. **Prescribe** ([conversion-contract.json](conversion-contract.json)):
   formats, rounding mode, the stages S1 (exact rational → 16-digit text),
   S2 (native read), S3 (native write at writePrecision 16) and S4 (native
   reread), each with its exact error bound and its branches; the
   floating-point operation model, including contraction and underflow; the
   per-operation bounds of the native face, cell and closure computations;
   the branch-decision rule; the accumulation budgets; the margin rule; the
   admissibility argument for a later native input.
2. **Pin.** From the pulled image only: manifest digest and platform; SHA-256
   of every file of the OpenFOAM platform directory and of the C and C++
   runtime libraries; ELF machine; the compiler string in `.comment`; the
   dynamic imports that fix the `long double` path (`strtold`,
   `__trunctfdf2`); the bytes of the exported binary64 constants and mesh
   thresholds; the build strings (`_be01ca78-20240625`, label and scalar
   sizes); the fused multiply-add instructions inside the geometry
   functions; the image `META-INFO` source manifest against the git blob ids
   of the archive members read above. Every value is compared with the
   runtime matrix row `opencfd-v2406-runtime`.
3. **Primary reader** (`fpchain.py`): applies S1–S4 to the frozen witness
   classes and to every rational pinned in the certificates (domain
   endpoints, recorded thresholds and intervals), with hardware binary64
   and exact `Fraction` arithmetic; evaluates the frozen synthetic
   reference cells exactly, unfused and fused, and checks each result
   against its prescribed bound; computes the certified margins.
4. **Independent reader** (`independent_reader.py`): does not import the
   primary. It re-derives every conversion and every binary64 result by
   integer-only IEEE emulation, re-reads the certificates from their pinned
   files and compares bit for bit with the primary receipt.
5. **Gate.** A new ledger revision in which only G04 changes, submitted to
   the unchanged `baseline-20261106/baseline.py` evaluator.

## Acceptance criteria

- **Pin:** the pulled manifest digest equals `identity.image`; its platform
  is linux/arm64; the SHA-256 of `checkMesh` equals the pinned
  `executables.checkMesh`, and every other pinned executable present matches.
  One mismatch refuses the pin; the refusal is kept.
- **Constants:** each exported constant and threshold read from the binary
  equals the binary64 rounding of its source literal, bit for bit.
- **Conversions:** for every witness and every certificate rational, the
  primary and the independent reader agree bit for bit on every stage, every
  stage error is within its prescribed bound (checked in exact rational
  arithmetic), and every frozen witness class is covered: finite, subnormal,
  near zero, signed zero, the ±VSMALL and ±VGREAT branches, a 16-digit tie,
  the label-token branch, failure of the 16-digit round trip in both
  directions, and a double-rounding case of the native reader.
- **Operations:** for every reference cell, the exact value, the unfused
  binary64 result and every prescribed fused pattern lie within the
  prescribed bound; closed-cell and closed-boundary sums are reported as
  computed (an exact rational zero is not taken as a floating-point zero);
  each guard and threshold comparison is classified decided or undecided
  by the branch rule, never by choosing a point.
- **Certificates:** each pinned certificate is read from its committed file
  with matching SHA-256; all 153 boxes (leaves 1778–1930), both domain
  endpoints and the two undecided determinant leaves 1929 and 1930 are
  carried unchanged; margins are computed exactly.
- **Gate:** only G04 differs from the 2026-11-12 ledger; the opening rule and
  every other gate are inherited unchanged; G04 is not marked
  `engineering_passed` unless the unchanged evaluator accepts it.

## What is refused

- Deducing an exact round trip from writePrecision 16, or a floating-point
  cancellation from an exact rational cancellation.
- Choosing a ratio, a point of the domain, a candidate, a dictionary or a
  native input to make a check pass; subdividing the certified domain;
  relaxing a threshold; dropping an endpoint, a box or an undecided branch.
- Treating a static or source fact as an observed execution, or the amd64
  sibling image as the pinned runtime.
- Any claim about flow, power, a physical turbo or manufacturing.

## Failure handling

A refused criterion is recorded with its reason and kept; no threshold, case
or witness is changed afterwards to make it pass. If the pin fails, the
conversion work still runs but the gate attestation records the mismatch.
