# Continuous sheets without a Boolean operation on their outline

This branch builds new support material from each free interval `D`. It keeps
all the triangles of `D`, then adds vertical quadrilaterals only on the edges
fully attested by the source interfaces. The declared penetration remains 0.2 mm.
An interface with the Z=0 plate receives no material below the plate.

Triangle edges are subdivided only at IEEE coordinates already present on
their same exact line. Their common oriented sub-segments cancel out. The
remaining cycles must describe a simple Polygon: signs and intersections are
evaluated with `Fraction`, including between holes and between adjacent
segments. A chain of all-positive triangles equal to this boundary excludes
gaps and overlaps of positive area by its winding number. An independent
inclusion also checks `D ⊆ R`.

Each quadrilateral is tried in the stable order of the source edges. It is
explicitly discarded if adding it prevents a simple sheet from forming; no
triangle of `D` is removed. A partially attested edge gets no extension: no
approximate intersection is created. Exclusions, the interfaces used and the
contacts are kept in the receipt. This policy increases the continuous
interfaces to be detached after the build.

Containment is still checked against the exact union of the vertical sweeps of
the original triangles of `D`, with the same plate plane. The envelope derived
from a GEOS union and its difference area remain separate diagnostics. The
compiled integer half-planes only speed up the search for a convex primitive:
the primitive choices and rational certificates remain those of the previous
check. Distinct free intervals cannot share a positive-length material segment.

`combinatorial-evidence/fixtures.json` contains three witnesses and two real
intervals from the 993 concept supports, with the digests of their results. The
replay checks the boundaries produced and their exact proofs. A horizontal roof
witness was also sliced on 170 real 60 µm planes; the last three layers do
intersect the body after the 0.2 mm penetration. These local results do not
constitute admission of the complete support. The material graphs, the six
admissions and the audit of all exposures remain necessary.

The v2 sources, their runs and their refusals are kept. The new entry points
are `generate_prism_region_v3.py` and `generate_legacy_region_v3.py`, with the
same positional arguments as v2. They copy their sources before computing and
keep the historical diagnostics. The part mesh and its complete cache of 1,034
layers remain identical.

Targeted native check:

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p 'test_carrier_combinatorial_*.py' -v
```
