# 917 reciprocating assembly: experiment under assumptions

Follow-up requested on 10 October 2026: « Continue avec des hypothèses » ("Continue with assumptions").
[The parameters](assumptions.json) define an assumed partial engine,
without identification of the specimen or metrological registration to the scan.
The [PicoGK C#](Program.cs) builds four families; the
[Python driver](run.py) exports twelve instances of each, i.e. **48 instances**,
and checks the geometry and a shared-crankpin kinematics.
The piston is hollow, with crown, skirt and two pin bosses. This is not
a complete engine nor an assembly accepted for operation.

## Starting assumptions

| Parameter | Assumed value | Origin and limit |
|---|---:|---|
| Bore × stroke | 85 × 66 mm | secondary documentary lead for the 4.5 L variant, specimen not identified |
| Connecting-rod centre distance | 132 mm | old schematic assumption, no measured Porsche dimension |
| Longitudinal / central pitch / bank offset | 118 / 173 / 37 mm | rounded external estimates from the scan, assuming 1 mm per unit; negative bank offset towards positive X |
| Cylinder base / length | 70 / 122 mm | study choice from an arbitrary crankshaft axis |
| Outside diameter / fins | 95 / 110 mm | study choice, eight 3 mm fins at a 14 mm pitch |
| Piston diametral clearance | 0.2 mm | study choice, not resolved by the 1 and 0.5 mm grids |
| Piston height / skirt / crown | 44 / 3 / 4.5 mm | choice after rejection of the solid piston; thermal and mechanical strength unknown |
| Inner start / boss diameter | ±20 / 32 mm | choice to clear the small end, engagement and clearances to be qualified |
| Phases of the six pairs | 0°, 120°, 240°, 60°, 180°, 300° | assembly assumption, not evidence of firing order |

The reference frame is not registered to the scan. The axes are levelled by assumption.
The other dimensions, densities, pressures and speeds are explicit
choices in the JSON. No assumed parameter becomes a measurement.

## Results executed on the Mac

The [text record](execution-20261010.json) contains the digests of the sources,
private exports, audits and scenarios. The final execution `run-005` uses PicoGK
2.3.0, .NET 9.0.317 and the two grids with constant target geometry.

| Family | Derived triangles, 1 mm grid | Derived triangles, 0.5 mm grid | Volume change / fine volume | Deviation from analytical volume, fine grid |
|---|---:|---:|---:|---:|
| Finned cylinder | 257,696 | 1,042,544 | 0.691 % | 0.224 % |
| Hollow piston with bosses and pin hole | 88,612 | 357,896 | 0.482 % | not evaluated |
| Two-eye connecting rod | 36,420 | 147,536 | 0.887 % | not evaluated |
| Hollow pin | 19,008 | 75,816 | 0.754 % | 0.253 % |

These two levels show a change in volume; they do not demonstrate
asymptotic convergence or local accuracy of the interfaces.
The four derived families are closed, oriented, of positive volume and
single-component, with independent probes in the holes and in the material.

The native STLs contain zero-area triangles: 120/240/16 for
piston/connecting rod/pin at 1 mm, then 1,440/316/524/56 for the four families at
0.5 mm. They remain kept and rejected as they are. The
[existing](../../../twins/m64-cylinder-head/source/picogk-local-junction/exact_zero_countertrial.py)
numerical witness is reused for a derivative that removes only the faces whose float64
cross product is exactly zero. No proximity threshold, vertex
displacement or orientation change is applied. A digest of the oriented
faces and an independent audit verify the derivative. This does not prove a
symbolic equivalence of continuous surfaces.
The initial trial `run-001`, stopped on the raw piston, and `run-002`, prior
to the interference check, remain kept outside Git. `run-003` keeps the
solid piston rejected for interference. `run-004`, the first hollow piston, remains
rejected after removal of the zero faces: 670 edges with incidence greater than
two, 615 components. No hole filling or vertex displacement
forced its acceptance. The height and crown were then revised
to avoid nominal tangencies; `run-005` passes the mesh screens.

The kinematics sweeps 360° in steps of 1°. The two banks use the same
transverse crankpin position; their piston axes follow the two opposite
roots of the connecting-rod closure. The stroke is 66 mm and the maximum closure
error is 5.69 × 10⁻¹⁴ mm. The analytical second derivative is also checked
by finite differences in the tests.

**Useful rejections:** centre distances of 120 and 144 mm do not keep the whole skirt
in this assumed cylinder: axial margins of −5 and −7 mm. The 132 mm centre distance
gives +5 mm on this single criterion. The sixteen small-end probes
(eight angles, two banks), inside the material of the solid piston of `run-003`,
are outside the material of the final hollow piston. The observed defect is corrected at
these probes; this sampled check covers neither all possible
collisions nor the minimum clearances. A complete check of the swept volume remains
necessary. Pin, bearing shell and retention clearances are not defined.

## Candidate materials and first load envelope

| Family | Study candidate | Assumed density | Mass per prototype, fine grid |
|---|---|---:|---:|
| Cylinder | AlSi10Mg | 2,700 kg/m³ | 0.621 kg |
| Hollow piston | forged aluminium | 2,700 kg/m³ | 0.186 kg |
| Connecting rod | Ti6Al4V, steel alternative | 4,430 / 7,800 kg/m³ | 0.193 kg for Ti6Al4V |
| Pin | steel | 7,800 kg/m³ | 0.084 kg |

The partial population with titanium connecting rods weighs 13.00 kg under these assumptions.
This is not the mass of the engine; the piston remains without rings or retainers.
The forged route for the piston is a conventional lead, not an LPBF material.
The aluminium LPBF leads are documented by
[EOS](https://www.eos.info/metal-solutions/metal-materials/aluminium).
No allowable limit from this supplier is transferred to these parts.

The eighteen scenarios cross two connecting-rod materials, 4,000/6,000/8,000 rpm
and 40/60/80 bar of assumed peak pressure. The reciprocating mass assigns
one third of the connecting-rod mass to reciprocating motion. The sum of the gas peak
and the absolute inertia peak constitutes an envelope; these peaks are not
assumed to occur together in an established combustion cycle.
At 8,000 rpm and 80 bar: 45.40 kN of gas, 9.67 kN of inertia with the titanium
connecting rod, sum 55.07 kN. Dividing by the nominal Ø18 section gives
216.4 MPa. The steel alternative gives 56.49 kN and 222.0 MPa. The mean piston
speed is 17.6 m/s. **These values demonstrate no material strength.**

Missing are the crank-angle combustion loading, temperature, bending,
buckling, contacts, bearing shells, cap bolts, stress concentrations,
fatigue and process defects. To adopt an additive route, it will require
grade/lot, machine and parameters, orientation, supports, heat treatment,
machining, surface finish, inspections and representative hot test specimens.
Titanium also requires a fatigue and galvanic isolation dossier.

## Reproduce and continue

```bash
PYTHON=/chemin/vers/python-avec-numpy-scipy-trimesh-rtree-networkx
DOTNET=/chemin/vers/dotnet-9
"$PYTHON" models/917-engine-reconstruction/hypothesis/run.py \
  --output work/917-hypotheses/nouvelle-execution --dotnet "$DOTNET"
"$PYTHON" tests/test_917_picogk_hypotheses.py -v
```

The STL/VDB files, the assembly, the transforms, `kinematics.csv`, reports and
visualisations remain private in `work/`. The C# and JSON sources are
editable and tracked in Git. The public directory contains textual
results, with no scan or derived geometry. No catalogue part record
receives a validation or manufacturing status.

The twelve targeted tests of the two steps pass; the C# compiles without
warning or error. `make check` ran 3,626 tests, 153 skipped,
and stops on two exact floating-point comparisons in the unchanged
993 impeller/stator directories. The other global targets are therefore not
reached locally. The targeted checks are rerun after the piston
revision; the CI of the latest commit remains to be observed separately.

The next step is to refine the piston and the pin/connecting-rod interfaces, define
the caps and bearing shells, then rebuild crankshaft, bearings and case
around the [interfaces to be measured](../README.md#interfaces-and-load-paths-to-establish-before-any-functional-part).
The cylinder heads, valve train, rings, lubrication, cooling,
balancing and physical tests remain to be done. The assumptions allow
the calculation to advance, without replacing these measurements or professional review.
