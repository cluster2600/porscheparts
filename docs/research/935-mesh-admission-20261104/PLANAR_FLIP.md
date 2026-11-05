# Full-surface planar-flip trial — 2026-11-04

This executes the next boundary-triangulation experiment following the
[retained-mesh audit](README.md). **The geometry screen passes, but the candidate
is not advanced to volume remeshing: its quality improvement is negligible.**
It does not complete faithful CAD, functional simulation or metal print release.

## Method and admissibility

Use the exact recovered coarse study boundary, not the raw scan as a remeshing
input. Its unresolved inferred closures and assembly/hardware identity remain
limitations. The original scan arrays are used only for independent distance
assessment. Both input hashes were checked before and after execution.

The first experiment deliberately changes connectivity only: PyMeshLab planar
edge optimisation, crease/planarity threshold 0.001 degrees, mean-ratio metric,
zero post-relaxation iterations, all faces. No coordinate smoothing, feature
redesign or volume meshing is performed. These parameters use the installed
[PyMeshLab filter API](https://pymeshlab.readthedocs.io/en/latest/filter_list.html#meshing-edge-flip-by-planar-optimization).
The fixed software screen required exact vertex preservation, equal face count,
no native intersections, sampled parent deviation below 0.001 mm, relative
volume change below 1e-6 and a decrease in bad triangle count. These are study
checks, not specimen/manufacturing tolerances.

An asymmetric planar quadrilateral control confirms that an actual edge flip
improves its worst triangle without moving vertices. A separate compiled CGAL
reader checks the full parent and candidate without repairing either one.
Closed-tetrahedron and crossing-triangle controls check this reader before the
real surfaces. CGAL's exact predicates/inexact constructions kernel is used;
degenerate triangles stop the intersection check rather than being excluded.
Libigl point-to-triangle distances assess 100,000 area-weighted samples in each
direction with fixed recorded seeds. This is sampled evidence, not a Hausdorff
bound or a physical tolerance certificate.

## Executed results and engineering decision

| Check | Observed result |
|---|---|
| Whole surface | 1,048,504 vertices; 2,099,584 triangles |
| Coordinates | Entire ordered vertex array unchanged |
| Connectivity | 560 face rows changed |
| Native geometry | Closed, valid polygon mesh; zero degenerate faces and zero self-intersection pairs, before and after |
| Worst triangle quality | Unchanged: 3.3035686e-6 |
| Triangle quality < 0.01 | 8,489 → 8,488 |
| Triangle quality < 0.1 | 85,069 → 85,059 |
| Parent → candidate sampled maximum | 1.3049e-6 mm |
| Candidate → parent sampled maximum | 1.4311e-6 mm |
| Scan → candidate p95 / sampled maximum | 0.10250 / 4.85946 mm |
| Candidate → scan p95 / sampled maximum | 1.55106 / 10.87647 mm |

The scan-distance statistics use the **coarse reconstructed assembly**; they
must not be compared as if they used the fine reference envelope. Large reverse
distances still expose inferred surface and incomplete observation support.

The initial software screen passes because it only required any decrease.
Its raw `accepted_for_next_study_stage` flag is therefore insufficient for
engineering admission. The separately retained `admission-decision.json`
explicitly withholds volume remeshing: removing one bad triangle leaves the
underlying boundary-quality problem essentially unchanged. No solver was run.
This rejection prevents a nominal software success from becoming an engineering
success claim. It also preserves the limitations of the predeclared screen.

The next materially different trial is a bounded isotropic remesh with explicit
surface projection, protected creases and independent topology/deviation checks.
Its allowed distance, quality-improvement target and topology constraints must
be recorded before execution. Do not vary interior tetrahedral size again just
to repeat the existing result. Missing physical geometry and calibrated process
inputs remain separate gates.

## Evidence and reproduction

The [aggregate trial receipt](planar-flip-trial.json) contains exact parameters,
versions, source hashes, native controls and assessments. Geometry and raw scan
arrays remain private under
`~/Developer/PorschePartsArtifacts/935-surface-flip-20261104/`, with a manifest,
argv, compiled inspector, source snapshot, original/candidate OFF, NPZ and raw
reports. The private job completed with exit code zero, without timeout.

Compile the read-only [CGAL inspector](source/inspect_surface.cpp) using the
installed Homebrew CGAL/GMP/MPFR headers/libraries, then run
[the trial driver](source/trial_planar_flips.py) with the hash-bound inputs:

```sh
clang++ -std=c++17 -O2 -I/opt/homebrew/include \
  docs/research/935-mesh-admission-20261104/source/inspect_surface.cpp \
  -L/opt/homebrew/lib -lgmp -lmpfr -o NEW_PRIVATE_DIRECTORY/inspect_surface
"$STUDY_PYTHON" docs/research/935-mesh-admission-20261104/source/trial_planar_flips.py \
  --solid RECOVERED_COARSE_SOLID_NPZ --input-sha256 HASH_FROM_AUDIT \
  --scan-arrays EXACT_SCAN_ARRAYS_NPZ --scan-arrays-sha256 HASH_FROM_SCAN_RECEIPT \
  --inspector NEW_PRIVATE_DIRECTORY/inspect_surface --output NEW_TRIAL_DIRECTORY
```

`STUDY_PYTHON` is the retained repair-trial interpreter with NumPy, PyMeshLab
2025.7.post1 and libigl; its actual versions are in the plan receipt. The original
outer launcher retains the 600-second bound; each native inspection has a
300-second bound. Replay into a fresh directory only. The binary's hash and
source are retained; compilation alone is not a geometry check. The CGAL check
covers validity, closure, degenerate faces and self-intersections; it is not a
complete anatomical or manufacturing inspection.
