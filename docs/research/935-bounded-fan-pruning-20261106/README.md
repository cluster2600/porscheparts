# 935 bounded smaller-fan omission study — November 6, 2026

A separately masked omission study removes 46 parent triangles and resolves all
42 inherited non-manifold used vertices. Full-resolution intersection predicates,
edge/winding and duplicate checks, independently replayed omission decisions and
actual saved-OBJ readback pass. All retained coordinates, oriented triangles and
provenance are exact. This is now a numerically admitted **conservative open
study surface**, not a complete faithful head or printable/functional part.

The [source-preserving parent](../935-contact-bridges-20261106/README.md) remains
immutable. This alternative deliberately omits 40 acquired triangles and six
previous inferred quarantine-patch facets. Their total parent-surface area is
0.2410318 nominal mm². Every omitted facet has retained correspondence and
distance probes. Small size is not evidence that these facets are erroneous;
the omission mask is an explicit reconstruction hypothesis.

The [reviewed scalar receipt](results.json) binds five new executed sources, six
frozen helpers, every private report and execution group, and the immutable
private payload manifest. Geometry, source IDs, face masks, raw journals,
nearest-point witnesses and full OBJ/NPZ files remain outside Git.

## Fixed policy and independent verification

Section 4 of the [scan reconstruction workflow](../../architecture/scan-repair-workflow.md)
permits bounded smaller-fan removal when used vertices remain non-manifold.
This is upstream of functional CAD/solver admission in the
[engineering architecture](../../architecture/README.md), under the
[local-compute decision](../../decisions/0012-local-compute-gpu-last.md).
The prescribed Qwen/CADAM/PicoGK/STEP/Gmsh/OpenFOAM/CalculiX/Adamantine roles
remain authoritative; this study does not replace them.

Before execution, the job fixes the following experimental bounds:

| Quantity | Bound |
|---|---:|
| Facets in each omitted fan | At most 3 |
| Area of each omitted fan | At most 0.05 nominal mm² |
| Fan bounding-box diagonal | At most 3 nominal mm |
| Iterative rounds | At most 4 |
| Total omitted facets | At most 256 |
| Sampled omitted-surface distance and sampled raw-source distance increase | At most 0.25 nominal mm |

At every current non-manifold vertex, retain the largest-area face fan, breaking
ties by the lowest parent-face ID. Admit a contact only if every other fan
satisfies all local bounds. Union the admitted omissions, enforce the total
bound, then recompute the whole used-vertex graph. Stop on convergence or the
fixed limits. No parameter is relaxed after examining a result.

Construction converges in one round, omitting 46 triangles. An independent
inspector reconstructs maximal source-face fans with a separate sparse graph,
recomputes all areas and sizes, replays every selection and union, and checks
the complete retained/omitted parent masks. It parses the actual saved OBJ
through the frozen independent reader. All face-level channels are preserved
under `parent_face_rows`; nothing is moved, welded, index-split or silently
dropped from correspondence.

The result retains 2,401,752 triangles and all 1,248,924 parent coordinates.
Eighteen vertices become unreferenced and remain in the source-indexed arrays;
they are counted separately from non-manifold **used** vertices. Full native
predicates find zero intersections and excluded degenerates. Independent
whole-mesh inspection finds zero duplicate faces, valid edge incidence/winding
and zero non-manifold used vertices. Physical omission validity is not proved.

## Boundary, component and distance accounting

The open surface has 98,720 boundary edges in 932 freshly enumerated walks.
Sixty-seven preceding boundary edges cease to be open; 25 newly exposed edges
are independently rejoined to the opposite edges of omitted parent facets.
Origin kind **5** records omission boundaries. Current counts are:

| Origin | Boundary edges |
|---|---:|
| 1 — raw acquisition | 97,863 |
| 2 — earlier quarantine | 100 |
| 3 — declared cut | 726 |
| 4 — inferred contact bridge | 6 |
| 5 — bounded smaller-fan omission | 25 |

Every walk has a fresh review row and raw-curve ancestor links. Kind 5 is not
relabelled as acquired geometry or blindly filled. Ten edge-connected surface
components remain; the largest has 2,394,447 facets and five components contain
one facet each. Their anatomy/assembly roles and any component selection remain
unaccepted. A passing manifold check does not establish a connected solid head.

Every omitted facet receives 1,000 deterministic area probes plus its centroid
and vertices: 46,184 probes in total. Their maximum sampled distance to the
retained surface is 0.2042844 nominal mm. The 219,476 preceding raw-source probes
are rerun; their largest distance increase is 0.2042238 nominal mm. Both satisfy
the fixed 0.25 study bound. The raw-source random sampled maximum remains
49.6927 nominal mm, including provisionally excluded attached components.
That component separation is still a hypothesis.

The reverse direction includes whole-candidate area sampling, all current
boundary vertices and explicit probes on **every retained inferred facet**:
52 facets, 52,208 probes. The source target still excludes only the eight recorded
zero-area original triangles. Exact retained source coordinates do not remove
the need to expose the omitted surfaces and inferred-patch errors separately.
All probes and nearest-face/nearest-point witnesses remain private and replayable.

Units follow the owner-declared convention of one OBJ unit per millimetre.
Independent physical calibration is unverified. Sampled maxima are not Hausdorff
bounds, and neither the omission limits nor passing them establish dimensional
or manufacturing tolerances.

## Next source-gap admission and reproducibility

After whole-topology and omission-deviation checks pass, all 932 walks are
screened. Of 898 acquisition-only walks, **286** pass the fixed experimental
source-gap admission: 3–128 edges, diagonal at most 3 nominal mm, fitted-plane
residual at most 0.25 nominal mm, adjacent-normal absolute-alignment p10 at least
0.8, no repeated source-coordinate visits, and an independently checked exact
simple dominant projection. Acquired coordinates and boundary owners are
rejoined to the original scan; contact with original intersection vertices is
excluded. The 34 other-origin/mixed walks are outside this admission.

Every current walk has a decision and reasons; rejection-reason counts overlap.
This admission does **not** run a native constructor or create cap geometry.
Known-hole/unselected-opening controls, exact masks, complete native trials,
independent whole-candidate checks and all new-patch deviation probes remain
required. No physical opening role or closure authority is accepted.

Four bounded execution groups complete with all owned children reaped. Private
ledgers pin commands, inputs, source hashes, outputs and stop rules; replay via
the frozen `run_local_delivery.py --plan <ledger> --output <fresh-directory>`.
Each group has a 600-second shared wall bound, sampled 4-GiB child RSS limit and
4-GiB disk floor. Sampling is not an operating-system hard memory cap. The
unchanged isolated Python 3.12.13 / NumPy 2.5.4 / SciPy 1.18.1 / libigl 2.6.3
runtime is used. Frozen sources and artifacts are never edited in place.

Twelve synthetic tests cover maximal fan partitions, largest-fan retention,
forged metrics, complete masks, area/size/count/round/total bounds, boundary-edge
cancellation, exact gap projection, normal/size gates and bounded predicate
cost. Public CI verifies those contracts and source/receipt consistency without
the private scan; it cannot certify the full-source measurements or fabrication.

No new paid compute or Vast resource is created. The scan is permitted on Vast
for prepared jobs within the existing $35 total / $30 compute / $5 reserve
budget. No external AI/CAD scan transfer, supplier outreach, merge or physical
release occurs. Interfaces, hidden geometry, complete faithful solid, admissible
volume meshes and correlated physics, material/machine/process qualification,
physical build/inspection and professional engine review remain open. The
inherited hypothetical Gmsh domain still fails 996 minSICN cells. The full goal
stays active; conservative-study admission is not manufacturing approval.
