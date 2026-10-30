# 935 study geometry: Vast printability diagnostics, 2026-10-29

The authorised Vast run inspected the unchanged coarse and fine reconstructions
from the [repair package](935-scan-repair-20261029.md). It produced thickness
probes, air-connectivity diagnostics, source-proximity maps and a topology
comparison. The recovered files passed SHA-256 verification, and instance
`58274262` was destroyed with its absence independently checked.

**Neither reconstruction is accepted for manufacturing.** This run found
resolution-sensitive topology and thin regions requiring review. It did not
change geometry, select a manufacturing process or execute functional CFD,
thermal, mechanical or additive-process simulations. The
[supported editable CAD and input contracts](935-scan-engineering-20261029.md)
remain the engineering baseline. Owner-confirmed scale remains one OBJ unit per mm.

## Results

| Diagnostic | Coarse reconstruction | Fine reconstruction |
|---|---:|---:|
| Triangles | 2,099,584 | 8,614,076 |
| Vertex-connected bodies | 1 | 1 |
| Euler characteristic | -1,288 | -2,934 |
| Minimum among 500 thickness samples | 0.0918 mm | 0.0954 mm |
| Median among those samples | 2.6922 mm | 1.9552 mm |
| Samples below 0.5 mm | 34 / 500 | 67 / 500 |
| Below-0.5-mm samples farther than 0.25 mm from observed triangles | 8 / 34 | 23 / 67 |
| Nominal enclosed air, 2 mm grid | 240 mm³ | 144 mm³ |
| Nominal enclosed air, 1 mm grid | 76 mm³ | 126 mm³ |
| Full thickness/orientation/2-mm-grid run | 179.0 s | 924.4 s |

Both meshes passed the inspector's closed, consistently wound, positive-volume
check. Their different Euler characteristics nevertheless show that topology
has not stabilised between these reconstructions. This does not identify which
handles or connections belong to the physical part.

Thickness probes are deterministic area-weighted face centres. The two probe
sets are not spatially paired, and the observed minimum is not a certified
minimum wall. The 0.5 mm and source-distance thresholds are diagnostic bins,
not supplier acceptance limits. A distance to the nearest observed triangle
cannot determine the error relative to an unobserved physical surface. The
private probe arrays retain the source-face associations for subsequent review.

Air classification uses approximate winding numbers at grid-cell centres and
six-connected flooding from **every** outer grid boundary. It does not fill
the solid's internal air. A 1 mm run sampled 9,607,584 cells per reconstruction.
Changing grid pitch changes the enclosed-air result; neither grid establishes
physical cavity closure, accessible powder removal or convergence. Six axis
orientations were measured as projected downward-area diagnostics; no build
orientation or support scheme was accepted.

## Execution and budget

The pinned mesh/CFD image ran on 36 effective CPU cores, approximately 64 GB RAM,
an RTX 5070 Ti and 120 GB of storage. These calculations used the CPU. The
contractual rate including disk was $0.25777778/hour. A separate local guardian
enforced a two-hour deadline and a $0.50/hour ceiling, and later verified absence.

The interval between the creation receipt and verified absence was 2,450.8 s.
Continuous billing at the full quoted rate would be approximately **$0.1755**,
before network charges. The observed account-credit decrease was $0.1562;
this is not a final invoice and may reflect posting delays. The retained
22 GB transfer planning allowance at the higher actual network rate adds
$0.08594 to a conservative estimate. The session stayed within the authorised
$30 compute allocation and $5 reserve.

The installed scoped wrapper needed a small offer-refresh correction: listing
50 offers and refreshing with a 1,000-offer query could change provider bundles
and reject a just-listed offer. The
[overlay](../../deploy/openbao/mesh-offer-refresh-scope.patch) preserves the
listing query while retaining the exact-ID, eligibility and price checks.
It was applied to a temporary copy of the existing installed wrapper, preserving
its other customisations. The historical, hash-pinned repository wrapper was
left unchanged. The overlay regression checks a temporary copy and verifies
that the frozen source remains untouched. No secret values were printed.

Initial SSH authentication failed despite matching public-key metadata. The
approved key's duplicate attachments were refreshed on this instance while
the provider reported it exited; direct SSH then succeeded. The wrapper's stop
waiter did not recognise that exited state and timed out. Destruction and final
absence were separately verified; no stopped rental was left behind.

## Reproduction and checks

The [public evidence manifest](935-printability-20261029/manifest.json)
binds the aggregate reports, runtime metadata and exact auxiliary drivers.
The main [inspector](../../scripts/screen_935_print_geometry.py) uses Python 3.12,
the [audit dependencies](../../scripts/935-faithful-requirements.txt), libigl
2.6.3 and, for the cloud runs, embreex 4.4.0.post1. Exact installed package
versions are retained in the evidence. The immutable original OBJ was freshly
hashed, and all coordinates and triangle indices in its cached array file
were independently compared with an unprocessed reload of that OBJ.

Six synthetic controls passed on Kali1 and Vast: known plate thickness, a solid
box, a closed air cavity, an open through-bore, exterior connectivity and invalid
or excessive grids. Kali1 completed the coarse thickness samples with values
matching Vast, but its full native cavity call aborted under a 10 GiB virtual
memory cap; the native failure's exact cause was not isolated. That partial
result is retained; the full cloud runs exited successfully. Peak resident
memory was 1,825,260 KiB for coarse and 6,721,972 KiB for fine. Software controls
do not qualify a head.

Run the inspector in a fresh private output directory, retaining the repository
layout for its existing sampling helper:

```sh
python scripts/screen_935_print_geometry.py \
  /private/935-head-reconstructed-study-fine-mm.npz \
  bcced05cf880809afc007b546f2f1ceba8fb5b71870ed8dd4fb6ea11bfdeb7aa \
  /private/new-fine-screen --pitch 2 --samples 500
python -m unittest discover -s tests -p test_935_print_geometry.py -v
python -m unittest discover -s tests -p test_vast_mesh_offer_refresh_patch.py -v
```

The private recovered package is
`~/Developer/PorschePartsArtifacts/935-scan-tools-20261029/printability-20261029/`.
Its README identifies the unchanged 3MF and editable CAD, the inspection image,
the indexed probes, the complete runtime recipe and recovery receipts. The
39 cloud files matched the recovered manifest; the archive SHA-256 is
`86bb5e050bc3e03124026ace38b02365b9bdce97552fd7311a4e095668882122`.
No raw or derived scan geometry, probe coordinates or private inspection image
is published here.

## Work remaining before a manufacturing file

Review the indexed thin regions and the resolution-sensitive connections against
the observations; retain unidentified components and unobserved surfaces as
unresolved. Continue source-supported CAD reconstruction and obtain accepted
functional interfaces before admitting the existing Gmsh/OpenFOAM/CalculiX cases.
Qwen/PicoGK assistance does not supply independent geometric acceptance.

Machine, alloy, thermal/mechanical material data, build parameters, support and
removal strategy, machining and inspection requirements are still unselected or
unverified. These are prerequisites for a process-specific build file and an
Adamantine analysis with meaningful calibration. Functional engine loads and
professional review remain separate gates. The Bryant Wolfe message remains an
unsent draft; this compute run grants no supplier-contact authority.
