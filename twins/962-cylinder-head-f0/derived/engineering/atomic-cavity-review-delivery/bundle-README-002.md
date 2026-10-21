# Atomic 962 head — exact numerical surface review

This bundle presents one numerical study surface with **901,727 vertices and 1,803,870 oriented triangles**. It is intended for inspection of the actual atomic candidate, not manufacture or engine installation. The canonical indexed BIN has SHA-256 `1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a`.

The local atomic report records zero triangles below the necessary triangle-quality screen. The evidence folders retain separate fixture, head-local, topology, directed-distance and scoped-feature records. Read each capsule's permanent scope and result; later evidence does not rewrite earlier ledgers. Surface checks do not establish an accepted tetrahedral volume mesh, solver convergence, material properties, thermal/strength/fatigue performance, LPBF process qualification, OEM fitment or manufacturing release.

## Open the mesh

Use `geometry/head-atomic002-exact.ply` for a standard binary PLY import. **Coordinates are millimetres.** PLY has no standardized unit metadata, so select millimetres in the importer. If software works in metres, the unit conversion is 1 mm = 0.001 m; retain the original file unchanged. Disable automatic welding, simplification, repair or coordinate rounding when reviewing exact correspondence.

The PLY stores double-precision x/y/z coordinates and triangle lists of three uint32 vertex indices. It carries no material, physics or manufacturing qualification. Importers may internally reduce precision; the supplied byte-level verification receipts describe the file itself, not an arbitrary viewer's internal representation. No viewer or renderer success is asserted by this format bundle.

`geometry/head-atomic002-candidate.bin` is the canonical `962SURF1` source. Its first eight bytes are that magic value, followed by two little-endian uint64 counts, then three little-endian IEEE754 binary64 coordinates per vertex and three little-endian uint64 indices per triangle. `geometry/head-atomic002-vertex-coordinate-origins.u64` contains one original-study vertex ID per output vertex; these are numerical provenance IDs, not measured Porsche interface identifiers.

## Verify correspondence and provenance

The format reports under `format/` must show that the completed PLY's every coordinate byte, triangle index, face order, winding, counts and bounds equal the canonical BIN. The writer and independent standard-library reader are supplied with their exact source-reuse provenance. No sampling, geometric regeneration or tolerance is used for that comparison. The archive's final member manifest identifies every delivered file and hash.

Each evidence capsule contains its own immutable receipt and integrity checker. Those checkers verify the sealed records within their stated scope; they do not rerun head physics or authorize use of the part. The exact source002 and shared include are under `source/`, without an executable, runtime image, full upstream header or original full-head geometry. `source/atomic_cavity.cpp` preserves historical source001, which was never compiled. The actual executable used `source/atomic_cavity_002.cpp` (source002).

Original project material retains the terms in `LICENSE.project`. Third-party source portions retain their own licences; see `evidence/fixtures/ATTRIBUTION.md` for CGAL scalar-predicate provenance and terms. Nothing in this review bundle is a physical or manufacturing approval.
