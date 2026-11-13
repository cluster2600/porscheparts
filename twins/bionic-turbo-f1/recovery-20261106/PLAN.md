# Bounded turbo evidence recovery

Issue #395 follows the re-evaluated G01 documentary and software-identity
gates. `prerequisites.json` records fresh matching executable hashes, both
successful evaluations, no running containers and the paused automation. The
new ledger accepts those two software prerequisites only; the parent ledger
and every historical receipt stay unchanged. No geometry, meshing, CFD,
performance or physical release is authorised.

## Selected prerequisite set and coverage

Recover these two real packages from their pinned public release assets:

- `airflow-internal-contact-obligations-20261014`: the superseding English
  contact package, one 833,717-byte archive and 28 files totalling 2,048,307 bytes.
- `airflow-native-face-tets-audit-20261013`: the native decomposition audit,
  three ordered parts totalling 2,436,456,992 bytes, reconstructing 60 files
  totalling 2,436,652,159 bytes.

They retain different representations and authority boundaries. This trial
covers two of the inventory's 63 archived packages, not all turbo evidence.
The other 61 packages, five directories without an archive receipt and
replication to a second host remain outside the trial. No earlier traversal,
contact proof, native mesh computation or case 084 is replayed.

## Method and limits fixed before application

Use new private directories under
`$HOME/Developer/PorschePartsArtifacts/turbo-recovery-20261106`.
Never overwrite an existing workspace, cache, store or archive. Preserve the
source volume, failed attempts and historical downloads. Maximum new storage:
40 GiB; require at least 50 GiB free before download. Keep Kali untouched:
its last verified native filesystem is full.

Use isolated CPython 3.12.11 and the existing free-tools dependency lock.
Read and reuse `benchmarks/free-tools/storage.py` for DVC archive and restore;
the carrier baseline and helper stay unchanged. Downloads use only the exact
allowlisted HTTPS release URLs, no credentials, a ten-minute limit per asset
and the declared byte-size cap. Check each part's SHA-256 and size before
ordered concatenation; independently check the reconstructed archive.

Before extraction, reject absolute paths, traversal, links, special members,
duplicates, unexpected files and mismatched sizes. Extract only the exact
file-manifest set into a new private directory. Independently hash every
payload. Do not execute anything from an archive.

Archive the selected artefacts with DVC into a new local store. Restore into
a separate empty workspace and cache, then independently rehash each restored
part, reconstructed archive and extracted payload. A successful push is not
recovery. DVC helper subprocesses keep their existing 120-second limit.

Exercise missing part, corrupted digest, path escape and stale manifest
failures using isolated mutations; original inputs stay intact. All rejection
controls must fail closed. Record exact coverage, hashes, tool versions,
commands and failure results. Publish only small receipts and code, never the
archives, native fields or raw mesh bytes. No deletion, remote upload, paid
compute, automation activation or physical test is part of this trial.
