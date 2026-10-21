# Frozen cap byte-extraction preparation

Held source only: no extraction, test execution, native operation or new geometry
has occurred. Root must review and authorize a fresh child before invocation.
The exact mixed keeper report is the completed local diagnostic, not an accepted
head/cap repair or a triangulation result.

`extract.py` selects the complete 3,508 cap face rows from the frozen reference,
then copies the 3,508 distinct source point rows in increasing global ID order.
It copies each binary64 XYZ row as 24 opaque bytes; only triangle vertex indices
are replaced with the corresponding integer local ID. Faces retain increasing
source-face ID order and their original corner order/winding. It performs no
mapping of the cap itself, quality calculation, CDT or coordinate arithmetic.
Finite/z=0 validation only checks the selected existing coordinate rows.

The five data outputs are:

- `cap.bin`: existing `962SURF1`, 8-byte magic, little-endian uint64 V/F,
  V little-endian binary64 XYZ rows, F little-endian uint64 ordered triples.
- `local-to-global-vertices.u64` / `local-to-global-faces.u64`: one little-endian
  uint64 source d2af local row ID per cap row; no Porsche/original894 lineage claim.
- `old-to-keeper.u64`: 1,222 sorted local-ID/keeper-ID little-endian uint64 pairs,
  including the 506 keeper identity rows and 716 nonidentity rows. It is a
  separate complete map-function serialization, not applied geometry.
- `fixed-face-ids.u64`: 38 sorted local cap face IDs, from the reference's exact
  exterior-cap records. Every vertex of those faces must map to itself.

The complete source and mapped loop sequences must match the saved diagnostic:
source 1,482/2,026; mapped 766/2,026, with the outer sequence unchanged. The
extractor does not prove loop geometry/domain equality. All group members and
keepers must be existing cap IDs; group membership is disjoint. Integer ID and
binary-byte checks are not a repeat of the diagnostic's exact quality query.

Before writing, all source/metadata pins and interpreter identity are checked.
Only a new task-owned output is permitted. Full emitted bytes are read back;
every coordinate row and ordered oriented face is then decoded and checked
against its actual selected source row. The manifest binds all five outputs,
records counts/loop identities and unchanged before/after inputs, and excludes
itself from its own output map. Failed/partial outputs are retained, never reused.
There is no internal RSS/deadline/CPU controller in this small byte utility; no
hard resource-enforcement claim is made. Root owns a separately bounded launch.
Full-source hashing streams bytes; geometry decoding reads only selected cap rows.

Two prepared stdlib test methods cover exact subset/reindexing (negative zero,
a nearly distinct binary64 coordinate, full readback and corrupted-byte refusal)
and a fixed-face mapping refusal. They import only the stdlib extractor, not
scientific/native modules, and have not been run by the preparer. The tiny byte
fixture is not an annular-cap or scientific-topology test.
