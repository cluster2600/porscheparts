# Horizontal 935 system — reference preparation

Stage on 3 October 2026: two scans prepared through PicoGK, interface requirements
defined, dimension research continued, then [executable system twin foundation](SYSTEM_TWIN.en.md):
complete functional registry, OpenUSD graph, six reduced models and measurement
comparison. Functional reference, improvements and calibrated twin remain to build.

## Independent contract before reconstruction

The [contract](interface-contract.json) defines **17 interfaces**: rotor/hub,
shafts, belts, transmission, bearings, support, engine, housing, guides,
lubrication, coupling and alternator; load paths and necessary evidence.
Axes, holes, faces, tolerances, scales and target engine variant are unknown.
Plausible dimensions cannot replace them. Coupling location must be identified
on the specimen; the supplier sheet cannot assign it.

The [documentary dossier](../../docs/research/935-horizontal-cooling/DIMENSIONS_AND_DETAILS.en.md)
separates base FIA form, Porsche 993 references and 935 reproductions. No commercial
field calibrates our scans.

## Executed scan processing

Preparation reuses the [existing programme](../993-engine-cooling-fan-system-f0/source/prepare_private_scan.py):
rigid PCA transform, retained inverse matrix and vertex order, removal only of
exactly zero-area triangles. PCA supplies convenient views, not a functional
axis or rotor/support positioning. Rotor back was neither realigned nor filled.

| Result | Rotor | Drive/support |
|---|---:|---:|
| Retained vertices | 624492 | 1256836 |
| Triangles after preparation | 1240439 | 2484656 |
| Removed zero-area triangles | 26 | 0 |
| Boundary edges after preparation and PicoGK | 8657 | 29476 |
| Boundary contours after preparation | 58 | 200 |
| Surface components | 2 | 1 |
| Boundary circles passing diagnostic filter | 0 | 0 |

[inspect_private_interfaces.py](source/inspect_private_interfaces.py) examines
boundary contours, fits plane/circle and requires angular coverage. Thresholds
are diagnostic filters, not machining tolerances. Contours also reflect coverage
defects; this filter misses bores internal to continuous surfaces and does not
segment all mechanical parts. The negative result establishes no measured datum.

## Actual PicoGK execution

[ScanReview](source/picogk-scan-review/Program.cs) uses `Library` without viewer.
Local kernel is **PicoGK Core 26.2.0**, native build `2026-06-05 21:50:16`.
C#/native library hashes remain in the summary. Local
[LEAP 71 project](https://github.com/leap71/PicoGK) source is at commit
`0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3`; this does not attest reused binary builds.

An annular synthetic control with chosen, known mm dimensions checks voxel
operations, volume and three inside/outside probes. At 0.5 mm/voxel, volume differs
from the analytical formula by **0.0556%**. This verifies runtime on the control,
not a fan or general geometric convergence.

Both prepared OBJ files were loaded as `PicoGK.Mesh` without voxelization. Every
triangle index was reread before export; fresh export audit retains boundary
counts without new zero area, non-manifold edge or orientation inconsistency.
PicoGK uses float32 positions: private receipts measure each scan's maximum
difference in unknown source units. It cannot yet be read as mm or compared to
functional tolerance. Surface intersections are not qualified by this audit.

## Local reproduction

Outputs use a new private directory outside Git or ignored `work/`. Inputs
remain unchanged. Python diagnosis requires NumPy/SciPy/Matplotlib; C# requires
.NET 9 and already qualified official PicoGK.

```sh
python3 twins/993-engine-cooling-fan-system-f0/source/prepare_private_scan.py PRIVATE.obj work/NEW/prepared --expected-sha256 RAW_SHA256
python3 twins/935-horizontal-cooling-system-f0/source/inspect_private_interfaces.py work/NEW/prepared/pose-normalized-open-scan.obj work/NEW/inspection --expected-sha256 PREPARED_SHA256
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-scan-review/ScanReview.csproj -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -p:BaseIntermediateOutputPath=/PRIVATE/obj/ -o /PRIVATE/bin
# Place compatible official native libraries next to the binary.
dotnet /PRIVATE/bin/ScanReview.dll witness work/NEW/witness
dotnet /PRIVATE/bin/ScanReview.dll mesh work/NEW/prepared/pose-normalized-open-scan.obj PREPARED_SHA256 work/NEW/picogk
```

[Limited public receipt](../../docs/research/935-horizontal-cooling/preparation-summary.json)
retains input/export/tool hashes and counts. Coordinates, transformations,
geometry and derived parameters remain private. Eight synthetic Python tests
cover tilted circles, incomplete arcs, nonplanar rings, degeneracies, pinched
boundaries, distinct surfaces and input/output protection. Six native CLI cases
verified open export, nonfinite/invalid-index/unknown-record rejection, SHA
checking and overwrite refusal.

## Visual rotor repair

Screened Poisson closure from [photo_guided_surface_repair.py](source/photo_guided_surface_repair.py)
is rejected after multiple-view review: closure invents hub/interblade volumes.
It remains a private attempt, never a reference, interface or calculation mesh.

[picogk-rotor-visual-proxy](source/picogk-rotor-visual-proxy/Program.cs) instead
creates explicit topology with a disk, hub and ten curved blades, aligned to
scan PCA envelope without millimetre conversion or interface inference.
[Proxy documentation](../../docs/research/935-horizontal-cooling/PICOGK_ROTOR_VISUAL_PROXY.en.md)
records audit and limits.

## Next required evidence

Identify variant, establish scale on two independent dimensions and verify
contract interfaces for a functional reference. Transmission interiors and
missing guides require appropriate documents/inspection. Specimen mass,
inertia, stress, drive, flow/pressure and cooling calculations need qualified
inputs. PicoGK processing alone establishes no real characteristic or quantified
improvement.
