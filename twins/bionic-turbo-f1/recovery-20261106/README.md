# Turbo evidence recovery — selected prerequisite set

This additive revision addresses #395 using the unchanged free-tools DVC
helper. It follows the verified Mac runtime baseline in PR #610. The parent
baseline, source volume, archive releases, carrier pilot and historical failed
studies remain unchanged. The recurring turbo automation stays paused.

## Scope fixed before execution

The [plan](PLAN.md) selects the superseding English internal-contact package
and the native face-tets audit. They are different representations and remain
separate. The [package manifest](packages.json) binds their source receipts,
payload manifests, ordered split parts, sizes, hashes and download URLs.
The [DVC manifest](dvc-manifest.json) registers the four compressed objects.

Coverage is **2 of 63 archived packages**, comprising 88 logical payload files
and two embedded manifests. The remaining 61 packages, five inventory
directories without archive receipts and second-host replication are not
qualified by this trial. Kali replication is pending storage capacity; a second
directory on the Mac is not a second-host backup.

The [G01 prerequisite receipt](prerequisites.json) records current successful
gate evaluations, matching binary hashes and the paused automation. The new
ledger accepts those documentary/software prerequisites for local recovery
only. Recovery does not authorise geometry admission, replay of the earlier
proofs, case 084, meshing, CFD, performance comparison or manufacturing.

## Recovery behaviour

The helper validates every compressed part before ordered concatenation,
checks the reconstructed archive, validates the complete TAR member set, and
independently hashes each materialised payload. Missing parts, changed digests,
stale manifests, path escapes, duplicates and unsafe links are rejected.
Output directories must be new and outside Git. A dangling output symlink is
rejected before its target can be created.

The first extraction rejected two historical TAR hardlinks and the embedded
manifest before writing any payload. [The declared revision](PLAN-HARDLINKS.md)
preserves that failure and allows only hash-identical references to an
allowlisted regular member. It writes independent regular files, never
filesystem links. Symlinks, external targets, link chains and cycles remain
rejected. No downloaded program is executed.

DVC archive and restore use an isolated CPython 3.12.11 environment matching
every version in the existing free-tools lock. The restore has its own new
workspace and cache, with `cache.type=copy`. Recovery is checked again from
the restored parts, followed by a separate `shasum -a 256` process and byte-size
check for each part, reconstructed archive and materialised file. DVC's own
object identity is not used as the independent SHA-256 result.

## Recorded result

The [DVC archive receipt](dvc-archive-receipt.json) and
[fresh-cache restore receipt](dvc-restore-receipt.json) bind the four objects.
The [contact](contact-receipt.json) and [native](native-receipt.json) readbacks
verify all 88 payloads and two embedded manifests. The
[independent check](independent-recovery.json) verified 96 files and
7,313,299,838 bytes, including reconstructed archives and split parts.
The [first failed attempt](first-attempt-failure.json) is retained.
The [control summary](controls.json) records seven recovery tests and two
native DVC tests, including corruption, missing objects and interruption.
The unchanged gate evaluator accepted the [G02 attestation](G02-attestation.json)
without blockers. Only G01 and this scoped G02 advance in the
[new ledger](gate-ledger.json); downstream gates retain their original state.
The next permitted work is a source-backed interface/operating ledger (#396)
or a prescribed conversion audit (#397), each with its own prerequisite
checks. Recovery alone permits neither native mesh admission nor a solver run.

## Reproduce in new private directories

Use the exact HTTPS assets and bounds listed in `packages.json`; do not use
unverified release tags as content identity. Install the existing
`benchmarks/free-tools/requirements.lock.txt` in a new Python 3.12.11 environment.
Keep every payload outside Git and preserve previous attempts.

```sh
TURBO_PRIVATE_ROOT="$HOME/Developer/PorschePartsArtifacts/turbo-recovery-new"
python twins/bionic-turbo-f1/recovery-20261106/recover.py contact \
  "$TURBO_PRIVATE_ROOT/downloads/contact" "$TURBO_PRIVATE_ROOT/contact-source"
python twins/bionic-turbo-f1/recovery-20261106/recover.py native \
  "$TURBO_PRIVATE_ROOT/downloads/native" "$TURBO_PRIVATE_ROOT/native-source"
python benchmarks/free-tools/storage.py archive \
  --manifest twins/bionic-turbo-f1/recovery-20261106/dvc-manifest.json \
  --root "$TURBO_PRIVATE_ROOT/downloads" \
  --workspace "$TURBO_PRIVATE_ROOT/archive" --store "$TURBO_PRIVATE_ROOT/store"
python benchmarks/free-tools/storage.py restore \
  --metadata "$TURBO_PRIVATE_ROOT/archive" \
  --workspace "$TURBO_PRIVATE_ROOT/restored" --store "$TURBO_PRIVATE_ROOT/store"
```

Then run the recovery helper for each package against
`$TURBO_PRIVATE_ROOT/restored/payload/<package>`, using new destinations, and
independently hash the outputs against the original pinned manifests.
The focused tests are `tests/test_bionic_turbo_recovery.py` and the existing
`test_free_tools.NativeDVC` tests in the DVC environment.
