# USD face-normal software fixture

The native author, full-content checker and independent known-array reader
passed on a **five-point, five-triangle software fixture**. The output is the
exact 1,433-byte [USDC](fixture/face-normals.usdc), SHA-256
`d7c33155a9efd091dd1cc4fa7b6cd86811ed7d7f2c8c3896848350c524499f51`.
This capsule contains no cylinder-head derivative or computed engineering field.

The [source](fixture/source.usda) deliberately includes an oblique triangle,
its reversed winding, a nearly distinct binary32 point, a duplicate triangle
and an axis-aligned face. It is not a manifold engineering mesh. Coordinates
use millimetres (`metersPerUnit=0.001`), Z up and an identity frame, with
`subdivisionScheme=none` and `orientation=rightHanded`.

Only one `normal3f` per face and explicit `uniform` interpolation were added.
The actual [checker report](reports/check.json) confirms every ordered point,
face count/index byte and all other canonical Sdf layer content remained equal.
The separate [known-array report](reports/known-arrays.json) compares both stages
with the [predeclared analytic arrays](fixture/expected-arrays.json), including
all 15 normal components. Its scope is narrower than the full-content checker.
Binary32 rounding bounds were fixed before execution; none were fitted to the
observed result. The pre-run card and individual reports keep their historical
execution/pending-check flags; later completed checks are recorded separately.

The four actual steps used the recorded native Linux x86_64 CPU runtime:
CPython 3.12.13, OpenUSD 25.5 and NumPy 1.26.4. The genuine tiny-source preflight
was ready; author, checker and reader returned zero and their workers were
reaped. Their complete 42/45/49/53 input maps were unchanged. Controllers record
affinity and address-space/deadline controls; peak RSS and CPU consumption were
not sampled. [Projections](projections.json) preserve those distinctions.

The [exact safe peer review](independent-review.json) contains all 130 original
captured-file inventory entries, four capture hashes and the deduplicated 53-pin
map. Its `prep/`, `steps/` and `validation-runtime/` paths are logical aliases.
The projection adds each stage's full membership in that map. Original receipts
and contracts are hash-bound, while private paths, commands, process identities,
runtime binaries and raw transport captures are omitted. These are explicitly
assembled allowlist projections, not complete native records or a standalone
reproduction/attestation of the original execution. The [root assessment](root-review.json)
and independent review read retained evidence without repeating native work.

Run `python3 verify_integrity.py` inside this folder for standard-library file
integrity and analytic-reference/report consistency checks. It does **not** open
the USDC or repeat native checks. Further USDC readback requires the recorded
OpenUSD runtime; that native readback already ran once. Exact source/test
snapshots preserve their original repository context and are provenance copies,
not a portable runtime bundle. Original material follows the repository
[licence](../../../../../LICENSE); third-party runtime code is not included.

This is a small software proof. No official minimum or full validator ran on
this fixture. It establishes no head validation, material or physics assignment,
solver fields, thermal/strength result, LPBF result, full Omniverse readiness or
manufacturing approval. The earlier [bore95 full-validation finding](../usd-full-validation-bore95/README.md)
remains separate. Head authoring and actual validators require their own fresh
preflight, bounded execution and review.
