# Wolfe Classics billet cylinder head scan for the Porsche 935

## Status

- Current level: `F0_reference`.
- Acquisition: OBJ purchased and downloaded on August 31, 2026.
- Use: local geometric reference for reverse engineering and simulation
  preparation.
- 993 compatibility: not demonstrated.
- Publication of the raw mesh: blocked until the redistribution right is
  explicitly documented.

The seller presents the cylinder head as designed specifically for a racing
Porsche 935 and as potentially adaptable to other 911s of the 1970s or 1980s.
That description does not cover the 993 and does not replace a comparison of
the interfaces.

## Local asset

The original file stays outside Git in accordance with the repository policy:

```text
raw-scans/wolfe-classics-935-cylinder-head/original/935-xtreme-cylinder-head.obj
```

Check digest:

```text
SHA-256 4623d5d3b73fe3d03ca988a47543a8dd1be7834d3040e6f7efd1e1e95c766486
```

This digest must stay identical for any analysis of the source file. A cleaned,
re-registered or simplified copy must receive a new digest and must never
replace the original.

## Initial inspection

| Property | Result |
|---|---:|
| Vertices | 1,281,608 |
| Triangles | 2,466,040 |
| X envelope | 197.899 OBJ units |
| Y envelope | 198.796 OBJ units |
| Z envelope | 227.098 OBJ units |
| Unique edges | 3,748,998 |
| Open edges | 99,876 |
| Non-manifold edges | 0 |
| Duplicate faces | 0 |
| Zero-area triangles | 8 |
| Groups, materials, normals, UV | absent |

The dimensions are consistent with millimeters, but the OBJ format declares no
unit. The mesh is not watertight; its signed volume must therefore not be
interpreted as a volume or mass measurement.

## Value for the twin

The scan provides a detailed envelope of the fins, bosses, openings and visible
studs. It can be used to:

1. locate the interfaces to be measured on a real cylinder head;
2. build section planes and collision envelopes;
3. prepare the intake, exhaust and chamber segmentation;
4. compare port architectures;
5. produce an independent parametric solid after the dimensions are checked.

It does not yet allow a reliable CFD computation. A flow simulation requires
complete internal surfaces, a closed fluid domain, boundary conditions and a
geometry representative of the cylinder head studied. The holes in the mesh
must not be filled automatically without distinguishing a functional opening
from a scan defect.

## Conditions for moving to the next level

To reach `F1_envelope`:

- confirm the unit using at least one known physical dimension;
- define a stable reference frame and orientation;
- separate the studs and add-on elements from the cylinder head;
- produce a lightweight proxy without moving the visible interfaces;
- document the uncertainty or a deviation map of the scan.

To study an interface with a 993:

- measure the bore and the chamber;
- measure the pattern, diameter and usable height of the studs;
- measure the gasket planes and intake/exhaust center distances;
- characterize the ports, seats, guides and valve angles;
- identify the material and mass of the cylinder head;
- compare these values with a 993 cylinder head of a known engine variant.

As long as these checks are missing, the scan remains a 935 reference and does
not join the active graph of 993 components.

## Provenance

- [Wolfe Classics product page](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan)
- Structured record:
  `catalog/sources/src-wolfe-classics-935-billet-cylinder-head-scan.json`
