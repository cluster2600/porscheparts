# Recovered runtime and held owner source generation

Issue #447 is still open. The exact missing Z3 executable has been recovered,
and all native005 census files are present and unchanged. A fresh owner source
generation is prepared for independent review; no actual contract, admission,
controller invocation or native run has been issued.

## Recovery evidence

The [Homebrew bottle update](https://github.com/Homebrew/homebrew-core/commit/af6aac9be7aa9bb9158db6607c13be5711f21090)
pins the arm64 golden-gate 5.1.0 archive. The public registry download was bounded
to 64 MiB and 60 seconds. Its 13,672,574 bytes match SHA-256
`7bce606885d161d03ead3e5966108aed2c95fda08c24d5ab656747db6922643b`.
Only the regular `z3/5.1.0/bin/z3` member was copied into a new private directory;
no archive filesystem paths or symlinks were extracted.

Its 16,244,496 bytes match the historical executable SHA-256
`b9a2c3a7dc833da652955116ad743cc733aa7938dbe64f528f71cb09066e2512`.
An isolated five-second `-version` check returned `Z3 version 5.1.0 - 64 bit`,
exit zero, empty stderr and the same post-run hash. `otool -L` reports only
system libc++ and libSystem dependencies; this is not full transitive ABI proof.
The Homebrew 5.3.2 executable and alias were not modified.

The native005 post-return census was independently reread from the historical
worktree: **1,646/1,646 files, 460,184,668 bytes, all hashes and sizes matched**,
with no missing, changed or unexpected linked files. This was byte recovery
verification only, with no scientific decoding or native execution. The compact
summary binds the full private audit by hash.

## Held rebind

Run `source/controller_rebind_20261107/prepare.py` from the head directory with
the selected Python 3.10.11 and `-B -I -S` to reproduce the preparation on the
owner host. It requires the recovered exact solver and a fresh fixed destination;
an existing preparation directory is never overwritten. The actual preparation
already exists in the historical worktree's ignored `work/962-engineering/`
directory. Do not rerun it into that directory.

The generator reads four hash-pinned published source originals. It changes
only the prep/output locations, the explicit route to the identical solver,
derived transport hash/size and source-choice digest. Each replacement is
unique and reverses to the original bytes exactly. `source-delta.patch` is the
complete source change; `bindings.json` pins every generated output. The fixed
protocol remains unchanged. Lifecycle, sampling, ownership, cleanup, arithmetic
queries and 40/48/56/60-second limits are unchanged.

The earlier source-choice contract requires: "Whole-source inverse and AST
equivalence outside the finite fixed constants/pins; transport remains exact
T003 and protocol exact." This generation changes T003's solver route, so its
prior source acceptance cannot be silently transferred. The new source choice
and bindings explicitly keep independent review and execution authorization
false. The old first-attempt EPERM behavior is retained, not suppressed. The
owned-group diagnostic in PR #618 narrows its cause but does not qualify the
full controller.

## Remaining closure

An independent reviewer must assess this exact delta and its route bindings.
Then prepare a fresh finite actual contract and current runtime decision, bind
the accepted original reviews only where their scope still applies, and issue
one new admission. The external observer must cover startup, return and final
census within the unchanged 60-second bound. Retain any refusal without retry
or promotion. Review saved results independently and assess native005 fields
under their unchanged scientific checks. Native003 is never issued.

This is associated with workflow phases `volume`, `material_strength`,
`lpbf_build` and `lpbf_release`. The complete 19-phase ledger from PR #618 remains
unchanged; no engineering phase or manufacturing gate is promoted. Three
portable tests reject modified or ambiguous sources, verify the generated
bindings and held status, and compare unchanged lifecycle functions and exact
deadlines independently through Python's AST. They do not execute the controller.
