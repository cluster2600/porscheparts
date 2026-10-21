# Imported-cube normalized software witness

One fixed **nine-node ASCII2.2 imported software cube** passed its discrete P1
check and separate complete Exodus geometry, sideset and field readback. This
does not qualify a head, continuum accuracy, material, thermal or strength model,
LPBF process, Omniverse field, PhysicsNeMo dataset or manufactured part.

The authored [-1,1]³ mm cube has 12 TET4 cells, volume 8 mm³ and 12 outward
boundary faces in sideset 11. It solves **−Δw=1, w=0 on the full boundary**;
**w has units mm²**, not kelvin. The exact discrete centre value is 0.25 mm²;
energy and integral(w) are 0.5 mm⁵ and reaction balance is −8 mm³. The actual
raw outward flux is approximately 6 mm³ against source 8 mm³: the **25%
continuum flux deficit** is retained. No mesh-convergence pass is claimed.

| Preserved stage | Outcome |
| --- | --- |
| Binary4.1 writer / first MOOSE import | Saved rows checked / unsupported format refused before solve |
| Separate ASCII2.2 writer | Strict reference-tag check failed after Gmsh renumbering |
| Pure integer-tag adapter | Restored tags with coordinate words, physical metadata and oriented connectivity unchanged |
| Separate ASCII2.2 MOOSE invocation | RC0, recorded reaping, unchanged inputs/runtime; final centre ≈0.25000000000000011 |
| Original / corrected saved-output assessor | Wrong Newton-sign expectation failed / separately corrected checker passed unchanged data |
| Separate Exodus reader and result peer | All nine coordinates and values, 12 cells, positive determinants, volume, outward boundary, opposed internal faces and complete sideset passed |

The saved Newton equation is J·y=F with free-row F≈−2 and y≈−0.25;
SNES updates w=u0−y≈+0.25 from zero. The physical source entry remains +2.
The corrected checker strictly requires those signs. It is a **post-run source
correction**; its peer arrived after the posthoc freeze and is not prior launch
authority. The original checker failure, all 22 native artifacts, initial path
mock-test failure and missing-$EndElements test failure remain distinct. No
solver rerun occurred during assessment. No complete node-to-PETSc-row map is
claimed.

The [combined result](proofs/combined-software-result.json) joins the exact
[corrected assessment](proofs/corrected-assessment.json),
[Exodus projection](proofs/Exodus-readback-projection.json) and
[independent result review](proofs/independent-result-peer.json). The
[inherited-text note](proofs/inherited-held-text-note.json) explains two stale
preparation descriptors in the unchanged readback child. They are historical
text: its 31 actual consumed-file bindings and completed readback are concrete.
Exodus times [0,1], FINAL nodal CSV suffix 0002 and scalar CSV time 2 remain
distinct steady-output bookkeeping, without a transient-time interpretation.

`data/` contains the complete small safe numeric arrays and explicit matrix,
vector and CSV token projections. Raw Exodus info records, runtime binaries,
private paths, commands, hosts and PIDs are excluded. Sources, primary-source
URLs/hashes, inventories and allowlisted lifecycle projections retain attribution;
runtime identity is not a complete dependency-build attestation. This assembled
whitelist selection is not full native records or standalone reproduction.
Code snapshots retain historical wording and private-invocation prerequisites.

Run `python3 -B verify.py` for **sealed byte integrity only**. It imports no
scientific library and neither replays numerical checks nor grants qualification.
