# Source-envelope-constrained analysis method

The first two CGAL head attempts passed exact source import and were then
killed by their declared **4 GiB and 8 GiB memory limits**. Neither established
an admitted solver mesh. The recovered 8 GiB checkpoint also fails an
[exact necessary fixed-face quality condition](FIXED_FACE_QUALITY.md).
The separate 12 GiB trial was **running, with its outcome pending**, when the
[preflight capsule](derived/engineering/analysis-envelope-12g-preflight.json)
was captured. That capsule credits no head result.
The [trial receipt](derived/engineering/analysis-envelope-trial-001.json) and
[runtime record](derived/engineering/cgal-envelope-runtime.json) preserve the
observed failure, exact source/binary/image hashes and package provenance.
Engineering, convergence, strength, thermal and manufacturing gates remain
false.

This is a separate method after the
[rejected VTK trials](ANALYSIS_SURFACE_ENGINEERING.md). It starts with all
902,145 original indexed vertices and 1,804,706 oriented triangles, without
STL tolerance welding. CGAL 5.6 `Surface_mesh_simplification::edge_collapse`
uses Lindstrom–Turk cost and placement with a
`Polyhedral_envelope_filter<Kernel, Bounded_normal_change_filter<>>`.
The physical source envelope is **0.25 mm**. Proposed placements and replacement
triangles must lie within that original envelope; the normal filter rejects
nonpositive old/new triangle-normal dot products. There is no face-count or
edge-count target. Permitted collapses exhaust or a time deadline stops the
trial. The [method contract](engineering/analysis-envelope-contract.json) was
frozen before the head attempt.

The filter constrains candidate-to-source deviation. Independent reverse
distance, completed two-sided continuous bounds, topology, feature/channel/BCC,
global intersection and minimum tetrahedral SICN **0.1** gates remain required.
The 0.25 mm envelope is an analysis discretization budget, not a manufacturing
tolerance. Neither the filter nor a completed run establishes admission.

Five small known-result envelope queries passed before the head attempt.
A subdivided cube collapsed from 48 to 12 triangles while retaining its
64 mm³ volume and corner coordinates within a 32-epsilon floating-point
roundoff bound. A coarse octahedron retained its eight faces and exact
coordinates/oriented connectivity because no collapse satisfied the filters.
Both initial native imports preserved their exact indexed source coordinates
and oriented triangle sets. Their independent continuous-distance intervals
closed using a fixture-only 0.01 mm gap. The tighter 0.0001 mm fixture query
first exhausted the existing allocation and remains recorded as incomplete;
the actual head requires the unchanged **0.0001 mm** interval gap.

The head attempt used native ARM64, two CPUs, no network, 4 GiB RAM, no swap,
a 285 s soft stop and a 300 s hard stop. The helper can save time-based
checkpoints every 30 s after accepted collapses. In this attempt Docker
confirmed `OOMKilled=true`, exit 137, after 5.435 s of native execution.
The exact imported initial surface is retained privately; no collapse
checkpoint or final candidate was produced. A resource failure cannot be
reported as a geometric rejection or success.

The separately frozen [8 GiB contract](engineering/analysis-envelope-8g-contract.json)
retained the same geometry, filters, two CPUs and deadlines. Docker again
confirmed an out-of-memory kill, exit 137. Two complete checkpoints survived;
the third file was empty. The original controller selected that last filename
and failed to read it. Its failure receipt and every native artifact remain
unchanged. The [8 GiB public capsule](derived/engineering/analysis-envelope-trial-002.json)
records a separate read-only recovery of the newest complete payload,
checkpoint 2: **876,577 vertices and 1,753,570 faces**. It retains the empty
checkpoint as rejected evidence. A focused regression now checks complete
payload selection; a complete but geometrically invalid newest payload still
fails rather than silently selecting an older one.

The recovered surface is closed and oriented, has Euler characteristic −208,
and its independent global CGAL audit completed with zero intersection pairs
and zero nonmanifold vertices. These are individual subgates. The two-sided
continuous-distance calculation exhausted its declared allocation, so no
distance upper bound or distance pass is credited. Feature/channel/interface
and convergence gates remain open. An independent Gmsh import retained every
coordinate and oriented face exactly. Full fixed-face quality screening and
the separate rational proof reject that checkpoint for any fixed-boundary
linear tetrahedral mesh requiring SICN ≥ 0.1. The preserved failed floating
fixture is described alongside the [exact proof](FIXED_FACE_QUALITY.md).

The initial 4 GiB contract omitted the hash of its imported Python surface
validator. The original frozen record remains intact; a
[separate observation](derived/engineering/analysis-envelope-import-audit-001.json)
records that provenance gap. The 8 GiB and 12 GiB contracts bind and snapshot
the imported validator before execution.

The [12 GiB contract](engineering/analysis-envelope-12g-contract.json) permits
one local case, with no swap, two CPUs, an 1800 s soft stop and 1860 s hard
stop. Observed charged memory reaching 11.5 GiB requests an orderly stop,
followed by a 30 s grace period. This protects resources and establishes no
geometric acceptance. Only the helper's deadline argument ceiling changed;
the 0.25 mm envelope and all admission gates remain unchanged. The
[new runtime record](derived/engineering/cgal-envelope-long-runtime.json)
and [repeated small fixtures](derived/engineering/cgal-envelope-long-fixtures.json)
bind its compiled source, binary and image before the head trial. Their
fixture-only 0.01 mm interval gap does not change the head's 0.0001 mm gap.
There is no automatic further resource or algorithm trial.

The dedicated local toolchain installed public `libcgal-dev=5.6-1build3` and
its apt dependencies into an owned container based on the already cached
ARM64 image. The runtime record binds the installed compiler, GMP, MPFR,
Boost, CGAL headers and image IDs. No shared runtime was modified. The helper
source and recipes are under [analysis-cgal](source/analysis-cgal/); exact
executed-source snapshots are under
[analysis-envelope-sources](derived/engineering/analysis-envelope-sources/).
The compiled binary, runtime images, initial surface and fixture geometry are
not part of the public source delivery.

The installed CGAL envelope and simplification policy headers declare
**GPL-3.0-or-later OR LicenseRef-Commercial**. No commercial licence is claimed.
Their original notices and installed package-copyright hash are recorded.
The original helper uses the public API and follows the repository licence;
no upstream example code was copied. This local runtime record does not
establish terms for a future commercial binary distribution.

Primary implementation and licence references:
[CGAL 5.6 source](https://github.com/CGAL/cgal/tree/v5.6),
[CGAL simplification documentation](https://doc.cgal.org/5.6/Surface_mesh_simplification/index.html),
[polyhedral-envelope filter](https://doc.cgal.org/5.6/Surface_mesh_simplification/classCGAL_1_1Surface__mesh__simplification_1_1Polyhedral__envelope__filter.html),
[CGAL licence](https://www.cgal.org/license.html).
