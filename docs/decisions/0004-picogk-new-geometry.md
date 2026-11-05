# ADR 0004 — PicoGK for new generative CAD

## Status

Accepted on 27 September 2026 (explicit decision by the project owner).

## Context

The full digital twin programme for the 993 Turbo engine (M64/60) involves new
geometry: cooling parts, cylinder head cooling volumes, brackets, ducts. The
existing chains (build123d/CadQuery in Python) remain the master source of the
artefacts already produced. The owner has decided: **new** geometry is written
in C# on the PicoGK voxel/SDF chain, without migrating the existing work.

## Decision

1. All geometry created from 27 September 2026 in the programme
   `M64-WHOLE-ENGINE-TWIN-0001` is implemented in C# / PicoGK (voxel-field
   workflow, implicit SDFs, Booleans), and ends with the repository-compatible
   mesh export call, verified against the installed PicoGK API.
2. Installed and verified scope: container `m64-engineering-worker`,
   .NET SDK 8.0.131, PicoGK 2.3.0 (commit `0e6cf6b6f499`, 2026-08-27),
   native runtime `/usr/local/lib/picogk.so`. The host dotnet (6.0) is not
   sufficient; compilation and execution take place in the container.
3. Existing Python/build123d artefacts are not migrated. They remain the
   dimensional reference for their areas; PicoGK does not replace the STEP
   truth where it already exists.
4. Physical parameters (wall thickness, clearances, blade count, lattice
   density, voxel size, export resolution) remain configurable, in line with
   the charter.

## Consequences

- A new .NET project building block (`M64.csproj`, target net8.0) is added to
  the repository; it modifies no existing Python chain.
- The reproducible chain (decision 0002) is still respected: build and
  execution run from the command line in the worker container.
- The fidelity levels (ADR 0003) apply unchanged: a PicoGK geometry is
  `F1_envelope` as long as its interfaces are not measured.
