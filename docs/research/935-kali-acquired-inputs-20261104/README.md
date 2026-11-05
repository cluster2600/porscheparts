# Acquired 935 inputs: native Kali copy and direct OBJ verification

Status: executed on Kali1's native ext4 filesystem, 2026-11-04. The complete
original OBJ and exact decoded arrays agree on **all 1,281,608 vertices and
2,466,040 triangles**. This qualifies the private input transfer and digital
source correspondence, not physical metrology, full CAD or manufacturing.

## Data refresh before more fitting

The known technical correspondence thread still contains three messages, dated
October 9, 11 and 14. The provider's October 11 clarification supports Xtreme,
cast then machined. It does not provide the exact specimen revision, measured
dimensions, internal drawings/CT, alloy or treatment.

A fresh, one-page query with the literal boundary `after:2026/10/14`, scoped to
the known subject and source names/domain, returns one result: the already known final owner reply. It has no
next-page token and supplies no new technical message. This is complete for that
specific query, **not an exhaustive mailbox search**. The inspected local
acquisition folder contains the original OBJ and two derived analysis files;
it supplies no additional metrology or CT in that folder. Other user locations
are not declared empty. No message or draft was changed, and the
[prepared technical requests](../935-readiness-20261104/PROCESS_DATA.md) remain
local documents; this operation sends nothing.

## Effective execution inputs without rewriting historical records

The [historical scan record](../../../catalog/scans/scan-935-xtreme-cylinder-head.json)
still names an old Kali path, uses the former billet description and records
unknown OBJ units. The corresponding
[source record](../../../catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json)
is SHA-bound by a separate
[historical source-authority record](../../../twins/reference-917-engine/head-architecture-authority-f45.json).
These records and stable source IDs are preserved. No historical path is
restored by guesswork and no other engine authority is changed.

The new [input contract](input-contract.json) records **1 original OBJ unit =
1 mm**, from the owner's existing instruction, and the provider's cast/machined
correction. Exact variant and alloy remain null; physical metrology and
manufacturing acceptance remain false. No second unit confirmation is required.
The contract is byte-identical to the one consumed on Kali and is pinned by the
[execution receipt](execution.json).

The fresh private Kali directory contains 21 files: the contract and 20 hashed
inputs. They include the original OBJ, exact arrays, original engineering
manifest, search frame, geometric partition, plane candidates, unchanged
interface contract, all eight chamber masks, the three historical fourth-region
section supports, the original intersection index and the streaming verifier.
Search axes/partitions remain analysis aids, not accepted anatomical datums or
body/hardware separation. The copied interface record keeps its original null
measurements and false functional gates.

## Transfer and independent raw-source check

Before transfer, every consumed original asset is checked against its known hash
or the original frozen engineering manifest. The local archive is assembled from
that exact allowlist. Its **197,437,440 bytes** and SHA-256 are verified again by
the receiver over the existing strict-host-key native SSH connection. All members
must be regular files and exactly match the checksum-bound contract; absolute,
escaping, duplicate or nonregular members are refused. An existing input
directory is refused. No user data is replaced or initialized.

The new Kali directory is mode 0700; all 20 listed input files are mode 0600.
The receiver also writes the contract with private archive permissions. The local
capsule directory is 0700 and its archive is 0600. Existing native SSH
authentication is reused; no credential values are extracted or logged.

On Kali, the verifier checks the contract hash and every listed file's bytes and
SHA-256, then reads the **original OBJ itself**, not a repaired mesh. It compares
every vertex coordinate and every triangle's indices/order directly against the
exact arrays. OBJ texture/normal index suffixes and negative relative indices
are handled explicitly; extra vertex/face records, nontriangular faces, changed
geometry and coverage mismatches are refused. No rounding, welding, clipping or triangulation
is performed by this check.

Five parser controls cover positive indexed/relative-index inputs and rejection
of changed coordinates, changed face order and a nontriangle. A separate receiver
fixture passes; five reason-specific controls refuse output reuse, a wrong
archive checksum, a symlink, path escape and duplicate members. Invalid archives
publish no input directory. Refusal controls run on synthetic bytes, never by
corrupting the acquired scan.

The Kali result is recovered and checked with its file hash. Transfer takes
0.98 s and bounded streaming verification 5.34 s in this run. These timings are
not comparative benchmarks. Source bytes remain intact on the Mac and the
private Kali copy remains available. No bytes are uploaded to an external CAD,
model, supplier or paid compute service.

## Runtime scope and reproduction

The existing native Kali Python is 3.12.11 with NumPy 2.5.4; SciPy is present.
**OCP is absent in this inspected interpreter.** The Python/NumPy source reader
is qualified here; the OCCT-dependent source-CAD helpers cannot be declared
runnable in this environment. Docker access and the complete solver/build chain
are not requalified. No runtime, privilege, Docker socket or existing service
configuration is changed. The contract explicitly keeps
`complete_engineering_chain_prepared` false.

Use the new private input root and the registered contract hash, not the absent
historical catalogue path. Verification is read-only except for a fresh report:

```sh
timeout --signal=TERM --kill-after=10s 600s "$KALI_PYTHON" \
  "$PRIVATE_INPUTS/source/verify_acquired_inputs.py" \
  --root "$PRIVATE_INPUTS" --contract-sha256 "$REGISTERED_CONTRACT_SHA256" \
  --output "$NEW_VERIFICATION_JSON"
```

The receiver reads an allowlisted tar archive from stdin and requires its size,
archive hash and contract hash. Actual SSH argv, allowlists, transfer/recovery
logs, results, controls and hashes are retained in the private local capsule:
`~/Developer/PorschePartsArtifacts/935-kali-acquired-inputs-20261104/`.
The fresh Kali root is under `~/porscheparts-private/`; its exact path is in those
private receipts. Existing roots and report files must not be overwritten.

The [engineering runbook](../../architecture/cadam-local-qwen.md) now links this
effective input path. The original scan, masks, model parameters, mail bodies and
raw fields remain outside Git. No paid resource is rented, supplier message sent,
fabrication ordered or physical gate promoted. The full faithful-head goal
remains active and incomplete; this operation restores verifiable acquired
inputs on Kali without inventing missing specimen or process information.
