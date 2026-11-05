# Whole-source metadata and connectivity audit

Status: executed on owner Kali1 and independently reinspected on the Mac.
This is source separation evidence, not a reconstructed bare head or an
accepted manufacturing domain. The [plan](plan.json) was fixed before execution.
It follows the [disk fitting rejection](../935-chamber-disk-fit-20261104/README.md)
and the [acquired-input qualification](../935-kali-acquired-inputs-20261104/README.md).

## Result

Both implementations parse every original OBJ triangle and preserve all
2,466,040 faces and 1,281,608 indexed vertices, including the eight previously
identified degenerate faces. No face is repaired, deleted or welded.

| Observation | Verified result |
|---|---:|
| Named objects, groups and materials carrying faces | 0 / 0 / 0 |
| OBJ records | Vertices and faces only; no comments or material libraries |
| Face components connected by indexed edges | 4 |
| Face-bearing components connected by indexed vertices | 4 |
| Component face counts, descending, for either partition | 2,458,749; 7,289; 1; 1 |
| Unique indexed edges | 3,748,998 |
| Edges incident to one source face | 99,876 |
| Unreferenced original vertices | 0 |

The complete edge and vertex partitions agree up to label renaming; checking
only their component counts would not establish that result. The Python
checker compares every component label with the independent C++ result and
checks the refinement relation. All eight fixed chamber selections belong to
the same largest component. The [seed summary](reports/seed-components.json)
also compares that component's complete membership across both implementations.
No raw source IDs or metadata strings are published.

The OBJ therefore supplies no named anatomical partition or unit/material
declaration. Its four disconnected components must not be called four physical
parts by size. In particular, selecting the largest component does not isolate
an accepted bare head. Manual source-supported classification remains possible
work; this audit does not prove it impossible. Owner-confirmed millimetres
remain the effective scale, without independent physical metrology.

The zero-unreferenced-vertex result concerns the original indexed mesh. The
earlier metric-domain exclusion of a vertex incident only to zero-area faces
does not make that vertex unused in the raw OBJ.

## Independent checks and execution

- [Python producer](source/audit_source.py): parse all original OBJ indices,
  compare them with the frozen decoded arrays, packed-edge sort, SciPy sparse
  components, private metadata state/spans and raw label arrays.
- [Native verifier](source/verify_source.cpp): separate endpoint-pair sort and
  disjoint sets; freshly parse all original OBJ indices and metadata assignments.
- [Partition inspector and controls](source/check_source.py): compare entire
  partitions up to bijection, source hashes, incidence census and fixed masks.
- [Seed summary](source/summarize_seeds.py): independently match the complete
  containing component in both label arrays; publish sizes, without identity.

The four controls cover a shared edge, a vertex-only contact, disconnected
triangles and a nonmanifold edge. The vertex-only control distinguishes the
two connectivity notions. Both implementations refuse the nonmanifold case
without a successful native output. Valid controls also exercise positive and
negative OBJ indices and named metadata states. See [controls](reports/controls.json).

Kali1 used its existing ext4 scientific Python environment and G++ 15.3.0;
the [runtime](reports/runtime.json) records exact versions and executable hash.
The five bounded stages all exited zero: compile, Python audit, native audit,
inspection and controls. Their actual timing and log hashes are retained in
the [execution summary](reports/execution.json). No cloud/model inference ran.
This Kali job does not claim an OS network sandbox. The scan stayed on the
owner's Mac/Kali infrastructure.

## Reproduction

Use new private output directories, the exact original OBJ, the exact decoded
arrays and the eight frozen selections. The acquired-input receipt supplies
their private owner-host locations. The plan pins the original/array hashes;
the selection contract pins each private selection file. Set `PY`, `OBJ`,
`ARRAYS`, `SELECTIONS` and a new `OUT` accordingly, then from this directory:

```sh
set -eu
mkdir -m 700 "$OUT"
g++ -std=c++17 -O2 -Wall -Wextra source/verify_source.cpp -o "$OUT/source-verifier"
"$PY" -B source/audit_source.py --obj "$OBJ" --arrays "$ARRAYS" \
  --plan plan.json --output "$OUT/python-audit"
"$OUT/source-verifier" "$OUT/python-audit/original-faces.i64le" "$OBJ" \
  1281608 2466040 "$OUT/native-audit"
"$PY" -B source/check_source.py inspect --arrays "$ARRAYS" \
  --python "$OUT/python-audit" --native "$OUT/native-audit" \
  --plan plan.json --selections "$SELECTIONS" --output "$OUT/verification.json"
"$PY" -B source/check_source.py controls --producer source/audit_source.py \
  --executable "$OUT/source-verifier" --output "$OUT/controls"
```

The optional seed summariser expects the selection contract at
`OUT/selection-inputs.json`, with its referenced selection files relative to
that directory. Run it only after the partition inspector succeeds. Writers
refuse existing outputs. Do not write into the frozen recovered capsule.

## Recovery, preservation and budget

The owner-host archive is 16,078,468 bytes, SHA-256
`16402aaf1f92f3e9936262fa1b9c7aa069c2a10e38139c6719f1d1fed6923c37`.
All 56 remote manifest entries passed Mac recovery checks. Mac partition
reinspection against the local exact arrays produces the same verification
report as Kali. See [recovery](reports/recovery.json),
[source audit](reports/source-audit.json), [verification](reports/verification.json)
and [receipt](reports/receipt.json).

The private capsule at
`~/Developer/PorschePartsArtifacts/935-source-separation-20261104/` retains raw
labels, face indices, metadata, execution commands, rejected controls, archive
and recovery. Its 80-file manifest hash is recorded in the public receipt.
The original OBJ, all 1,008 frozen atlas/reference files and all 63 CADAM/Qwen
coupon files remain hash-identical; see [preservation](reports/preservation.json).
Private raw geometry and account monetary values are excluded from Git.

The scoped OpenBao/Vast wrapper successfully reads account balance and
instances. All four known task instances (58274262, 58296618, 58306265,
59142713) are absent. This increment rents no machine and leaves unrelated
resources untouched. The original $35 limit, $30 compute limit and $5 reserve
remain unchanged. Account balance is not an attributable final task invoice;
the approved wrapper does not expose invoice line items. No final spend or
remaining task allowance is inferred from account-wide credit.

## Effect on the resumed engineering goal

The [CADAM/Qwen branch](../../architecture/cadam-local-qwen.md) remains an
independently checked synthetic proposal aid. It does not replace PicoGK,
source-derived native references, Gmsh, OpenFOAM, CalculiX or Adamantine.
This whole-source audit adds an upstream selection check; it does not adopt
any rejected primitive fit or alter existing native documents.

Next source reconstruction needs anatomically justified masks and interfaces,
with acquired surfaces distinguished from missing interiors. Neither OBJ
metadata nor component size provides those labels. The existing head study
envelope remains exploratory. Specimen metrology, hidden passages, material,
operating loads and a calibrated machine/material process remain separate
open gates. No new solver case, closed faithful head, machine-specific build
file, physical print or functional release is accepted by this increment.
