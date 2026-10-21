# Bore95 exact source-mesh OpenUSD preparation

The separately declared source-authoring route preserves all **1,804,706
original triangles** and 902,145 indexed points. Its complete oriented-triangle
digest equals the source digest; there are no missing or extra triangles and
the world-bound discrepancy is exactly zero. The [receipt](receipt.json) binds
the source, intermediate USDA, native USDC, original reader, writer, assessor,
interpreters and pre-run [contract](frozen-contract.json).

The existing STL reader reconstructs the original float32 triangle coordinates.
The [writer](../../../source/author_exact_usd.py) serializes them as source USDA;
the existing native OpenUSD runtime opens and saves a fresh USDC without CAD
conversion. Z-up, millimeter units, the original pivot, identity transforms,
right-handed orientation and `subdivisionScheme=none` are verified on output.
The official minimum USD reference passes all eight checks under a genuine
OpenUSD-component preflight. Full Asset Validator/SimReady dependencies remain
absent.

Four [regression controls](../../../../../tests/test_962_exact_usd.py) cover
nearly distinct float32 values, winding/duplicate multiplicity, preservation of
existing outputs/symlinks and invalid-source rejection. Native serialization,
strict audit and minimum validation took 1.58, 20.79 and 0.18 seconds, each
bounded to two CPUs, 6 GiB address space and 90 seconds.

Output metadata contains only the project authoring-route label and original
STL hash. No private paths, nonempty external asset dependencies, materials,
physical schemas or solver fields are authored. The 17.37 MB USDC remains a
private user-review artifact with verified byte-for-byte local readback.

The [rejected vendor derivative](../usd-bore95-conversion/README.md), its lost
faces and frozen receipts are preserved separately. This result accepts source
geometry preservation only. It establishes no historical fidelity, head
simulation, calibrated material, complete digital twin or manufacturing release.
