# Quality-constrained analysis-surface proposal

This generates a proposal from the complete retained PicoGK mesh. It leaves
the CAD master intact. The qualified build uses CGAL 6.2.1, Boost 1.90.0 and C++17.

```sh
cmake -S twins/935-horizontal-cooling-system-f0/source/analysis-simplification \
  -B work/NEW-quality-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE=-O2
cmake --build work/NEW-quality-build
ctest --test-dir work/NEW-quality-build --output-on-failure
work/NEW-quality-build/quality_preserving_simplify ORIGINAL.off NEW-CANDIDATE.off
```

Sharp edges above 0.25° remain constrained. Surviving triangles affected by a
collapse must have mean ratio at least 0.05, followed by the normal-change check.
The 0.1 edge-count target is a stopping request; constraints can prevent reaching
it. Existing bad triangles can remain. Validate the actual exported surface with
the independent [envelope checker](../analysis-envelope/), including topology and
self-intersections, then audit every volume cell and numerical convergence.
[Execution and rejected trials](../../../../docs/research/935-horizontal-cooling/ANALYSIS_MESH_CONTINUATION_20261022.md).
