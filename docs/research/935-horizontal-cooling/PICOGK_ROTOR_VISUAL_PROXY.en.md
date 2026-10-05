# PicoGK topology proxy for the 935 rotor

On 3 October 2026, axial, radial and oblique review rejected Screened Poisson
closure `run-009`: although numerically closed, it invents bridges and hub
volumes. It does not represent a rotor and must serve as neither visual
reference nor calculation mesh.

This stage's reference is therefore a **visual topology proxy** built with
PicoGK, expressly distinct from CAD recovered from the scan or any printable
part.

## What the scan establishes visually

The main component's top view shows a rear disk, ten raised curved blades and
a central hub. The prepared file also has a small isolated second component;
this reconstruction does not merge it into the rotor. Separation prevents
missing central coverage from becoming false hub geometry.

## PicoGK construction

The [Program.cs](../../../twins/935-horizontal-cooling-system-f0/source/picogk-rotor-visual-proxy/Program.cs)
checks the prepared scan hash, extracts only its PCA-plane envelope and builds
an implicit union of:

- a rear disk;
- a raised annular hub;
- ten regularly offset curved blades.

Radii, heights, thicknesses, curvature, bore and blade sections are **visual
assumptions parameterized by ratios**. PicoGK voxel spacing is in the unknown
source unit and is never claimed in millimetres. Scan coordinates, meshes and
the detailed receipt remain under `work/`.

A private execution used PicoGK Core 26.2.0. After welding vertices for audit,
the proxy is one closed component with consistent orientation; MeshLab checks
found no self-intersection or non-manifold geometry. These checks qualify only
the generated proxy's consistency.

## Reproducible execution

Execution requires an already qualified official PicoGK runtime, .NET 9 and a
new private directory. Output files must never be added to the repository.

```sh
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-rotor-visual-proxy/ScanGuidedRotorProxy.csproj \
  -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -o /PRIVATE/bin
dotnet /PRIVATE/bin/ScanGuidedRotorProxy.dll \
  /PRIVATE/pose-normalized-open-scan.obj PREPARED_SHA256 work/NEW
```

## Remaining limits

The proxy confirms neither 935 variant, scale, rear face, aerodynamic profile,
rotation direction, bore nor fastening system. It therefore supplies no mass,
inertia, speed, stress, flow or pressure. Interface metrology and separate
surface reconstruction remain necessary before a mechanical or fluid twin.
