# 935 corrected rotor: bounded analysis surface and fresh fluid-case input

This continuation uses the guarded PicoGK root correction reported in the
[preceding checkpoint](ROOT_MESH_RESUME_20261025.md). It concerns the **horizontal
935 rotor**. The shroud, drive, engine interfaces and complete cooling system
still require their own measured assembly and solver evidence.

The corrected STL is
`ee8f91167f6147edd125b2b4db9da65a5704aac95879a82f2aab6bada779f9ed`.
The independently indexed mesh is
`9128da15ba5ac3ea55373c792006478deb5dd77713d52d38a9eac7c4b70d0c8e`.
Both remain private. The [OFF preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_surface.py)
checks both hashes and reads back every coordinate and triangle. Its output
contains 660,003 vertices and 1,320,006 triangles, with SHA-256
`5cdd1b993029a80921f995636a3a980027a66af7c87fc33ba935f7bf3a6458cf`.

## Bounded simplification

The existing [CGAL simplifier](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/quality_preserving_simplify.cpp)
was built on macOS with the already documented
[input-facet protection patch](../../../twins/935-horizontal-cooling-system-f0/source/analysis-simplification/protected-input-patches-20261022.patch).
This preserves three rings around inherited thin facets rather than silently
removing them. The source and patch are unchanged. The local toolchain was
CGAL 6.2.1, Boost 1.92.0, Apple Clang 21.0.0 with `-O2 -std=c++17
-frounding-math`; Python 3.12.11, NumPy 2.3.5 and Trimesh 5.1.0 handled
independent readback.

| Check | Result |
|---|---:|
| Simplified surface | 438,652 vertices; 877,304 triangles |
| Simplified OFF SHA-256 | `c8aef379ac3a66188518ecc247fb1970ffe80fa33cea1b49b0b87db098959ac9` |
| Connected components / boundary or nonmanifold edges | 1 / 0 |
| Euler characteristic / genus | 0 / 1 |
| Original thin facets below quality 0.05 retained with identical coordinates and connectivity | 121 / 121 |
| Source-to-candidate and candidate-to-source complete envelope | Pass / pass |
| Envelope bound / reserved numerical margin | 0.0225 / 0.0025 source units |
| Candidate volume / relative difference from corrected rotor | 431,014.075493 source units³ / +0.00011006% |

The [independent continuous-envelope checker](../../../twins/935-horizontal-cooling-system-f0/source/analysis-envelope/tiled_envelope.cpp)
tested all 1,320,006 source triangles and all 877,304 candidate triangles.
Its self-test includes a counterexample in which vertex-only proximity would
incorrectly pass. Closed topology, valid triangle mesh and complete
self-intersection checks passed. The candidate retains the source's 121 very
thin faces; simplification has not claimed to repair those observed facets.
The bound is relative to the corrected *reconstruction*, not the raw scans or
an authenticated manufacturing tolerance.

## Fresh OpenFOAM input

The [case preparation source](../../../twins/935-horizontal-cooling-system-f0/source/corrected-analysis-20261025/prepare_fluid_case.py)
accepts only these exact source and candidate hashes and the passing
bidirectional certificate. It reuses the earlier Foundation 13 pilot's
unchanged system dictionaries, including mesh-quality SHA-256
`bafbc5ced7e83c5a1cc11291a0937c3499a6713e8e3411a83f93464381ba2c7d`,
and replaces the old rotor OBJ with the corrected candidate. The existing
export helper reads back every SI OBJ vertex and face. The new private case is
`work/935-corrected-analysis-20261025/fluid-case-001/`; its rotor OBJ is
`4ea77849439ac1b525d000386d8fa8e564a7f311552117262e4b55e29cb42528`.
One uncalibrated source unit is provisionally mapped to 0.001 m, as in the
earlier pilot; this is **not** a verified physical scale.

The [reduced machine-readable receipt](corrected-analysis-20261025.json)
identifies the source, candidate, case and private checkpoint. The private
[release](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
holds the OFFs, source copy, compiled controls, geometry receipts and case
without publishing scan-derived geometry in this repository. Its 20 archived
files were read back and hash-checked locally.

## Admission status

No new OpenFOAM meshing or CFD solve has run on this corrected case. The prior
snapped case used the old rotor and failed the full native `checkMesh` with
316,996 concave cells and two duplicate-face warnings. Its numerical results
cannot validate the new input. On this run, Kali1's Thunderbolt bridge became
inactive after the first successful SSH connection; the Mac Docker daemon
also did not answer an eight-second read-only probe. Neither service was
changed. No new Vast rental was created.

The next computational gate is a fresh mesh on this exact OBJ, with the same
complete native quality checks, boundary-layer evidence, resolved concavity
and duplicate faces, and a three-grid study. Airflow, pressure, torque,
mechanical strength, full 935 fitment and manufacturing remain unqualified
until their corresponding calculations, measurements and review exist.
