# Complete design engine: four valves and bionic turbos

This branch brings together **119 geometric definitions and 1,129 instances**:
12 four-valve cylinder head assemblies, 48 valves and two bionic turbos
of 39 components each. It covers the 44 families of the F1/F3 engine
programme, with their explicit modern replacements, and adds guides, seats,
double springs, retainers, studs, gaskets, pumps, circuits and accessories.
This scope of representation is complete; **the manufacturing bill of
materials and the functional definition of each part are not**.

The base of this new variant keeps the FIA bore/stroke of **85 × 66 mm**.
It is neither a homologated replica of the 917, nor the 90 × 70.4 mm model of
programme F33, nor evidence of its power target. The FIA dimensions pass the
documentary validator already used in the previous slice. The materials, the
modern interfaces and the new shapes remain hypotheses. The existing
catalogue grants no new qualification.

## What is reused

- The [four-valve air + oil cylinder head](../../../docs/studies/993-air-oil-20261002/README.md),
  its body and its 12 meshes of valves, seats and guides, exactly identified
  by the [published manifest](../../../docs/studies/993-air-oil-20261002/delivery-manifest.json).
  The new spring stacks follow the axes of the reused guides; their installed
  heights remain hypotheses. No change of scale is applied. A cylinder head
  derived from the 935 scan demonstrates no 917 interface.
- Our 39 components of the F0 bionic turbo,
  with no substitution by a K16 or Garrett envelope. Each mesh keeps its
  coordinates, triangles and digest. This dependency comes from another local
  branch, at commit `aba24fd351930ed4cee194b8cc557c3b80238894`, not yet
  available on GitHub at the time of the check. Provide its local delivery to
  the reconstruction programme; its editable sources are kept in the private
  delivery and are not published by this PR.
The ongoing F1 turbo work is not reused.
- The PicoGK generators for cylinder, piston, connecting rod and pin, as well
  as the kinematics and the FIA validator of the previous slices, left intact.
- The F1/F3 placement functions for the retained accessories. The replaced
  historical parts are accounted for: coil ignition, electronic injection,
  rocker arms and internal wastegates.

The native F50 master is documented in Git, but its private geometry was not
found in the local locations explored. The model integrated here is therefore
precisely the air + oil delivery of 2 October, not a reconstruction of the F50
master or an old generic F29 cylinder head.

## What is created with PicoGK

[engine_layout.py](engine_layout.py) defines the shapes, the bill of materials
and the placements; [design.json](design.json) exposes the mechanism
hypotheses and the material/process routes. [Program.cs](Program.cs) uses the
native PicoGK 2.3.0 kernel to build the components and save **separate STL
and VDB files**.

The half-cases have branched ribs between the bearing stations and the
cylinder envelope. The timing supports have radiating branches; the hollow
manifolds join six branches per bank. These bionic rules are a reproducible
parametric drawing, with no topology optimisation, load path evidence or
CFD/FEA performance. The envelope of these cases is itself a hypothesis: it is
neither registered nor fitted to the 917 scan. The shells derived from the
scan remain in the first slice; they are not replaced or declared compatible
by this new assembly. Their registration remains necessary before any
dimensional fidelity or integration of the real interfaces.

The crankshaft represents six shared crankpins, the declared phasing and eight
main bearings. Its webs have a limited axial thickness. The three grooves
proposed in each piston are subtracted from the earlier model, without
modifying that generator. The new cylinder starts at 50 mm and is 160 mm long:
it covers the assumed symmetric 86 mm piston and places the cylinder head
plane at 210 mm. These three values **do not come from the FIA**. The FIA
dimension of 43 mm is the axis–crown distance; the lower skirt of 43 mm
remains a hypothesis. The crankpin stays at the 52 mm FIA reference; the
connecting rod bore goes to 56.25 mm with an assumed radial allowance of
2.125 mm. The former bearing shell of about 1 mm did not remain connected on
the 1 mm grid. This choice makes the concept representable; it does not define
a working bearing shell.

A connecting rod bearing shell, a pair of collets and an accessory envelope
may be assembly units. The instance count does not claim to count each real
half-shell, filament, thread or gasket. Alternators, starters, sensors,
injectors, electronics and exchangers are bought-in envelopes; the gears are
blanks with no teeth or contact law. The internals of these bought-in
components are not redrawn.

The turbo rotations are proper, with no mirroring: their axis remains
longitudinal and their connections face outwards from each bank. The ends of
the new ducts follow the connection centres of the F0 concept: local hot inlet
`(43, 56,25, -99,75)` mm and cold outlet `(49, 42,25, 0)` mm.
These reused centres define neither flanges nor sealing tolerances.

An independent check selects the valve vertices whose local Z is less than or
equal to 4 units, near the joint plane. Under the hypothesis
1 unit = 1 mm, their maximum radius exceeds the 85 mm bore circle by
**6.238 mm at the intake and 6.445 mm at the exhaust**. This flags an envelope
incompatibility to be addressed, without by itself establishing piston–valve
contact. The chamber and the cylinder–cylinder head interface must be
reconstructed, or another documented variant selected; their compatibility is
not established by the placement of these parts.

## Reproduce and inspect

The programme requires a turbo delivery bound to the digests in
[imports.json](imports.json), .NET 9, PicoGK 2.3.0 and a Python environment
with NumPy, Trimesh, SciPy, Rtree, NetworkX and Matplotlib. It refuses
divergent digests, mixed FIA variants and overwriting an existing directory.
The generated geometry stays under the ignored `work/` directory.

```sh
python models/917-engine-reconstruction/assembly/run.py \
  --dotnet /chemin/vers/dotnet \
  --turbo-assets /chemin/vers/bionic-turbo-assembly-final \
  --output work/917-4v-biturbo-essai-001
```

Each 1 and 0.5 mm grid keeps its native STL, VDB and receipts. The independent
numerical witness already in the repository produces a derivative that removes
only the triangles whose cross product is exactly zero in float64. No vertex is
moved; no non-zero triangle is removed. The inherited meshes undergo no
removal. Closure, orientation, positive volume, single component and absence
of duplicates are inspected. Continuous fidelity to the scan and continuous
self-intersections are not certified by these checks.
These grids do not define bearing, ring or machining tolerances. The proposed
route combines printing of the candidate structures, machining, forged parts
and bought-in components; it does not plan to print the whole mechanism as it
stands.

The GLB export keeps the separate definitions and the 1,129 transforms, with
mm → m conversion. Reopening it checks names, counts, triangles and the
transport error. The PNG preview uses points sampled on the surfaces, for
presentation only; the STL files and the GLB keep the triangles of the checked
models. `assembly.json` contains the bill of materials, the placements, the
import digests and the F1/F3 coverage; `validation.json` records the motion
checks and the conflicts observed.

The add-on [render_surfaces.py](render_surfaces.py) reads the same GLB with
VTK 9.7.1 and produces four panels with **opaque, shaded surfaces**:
complete assembly, mechanism with cylinder heads, half-case with crankshaft
and legend. It keeps all triangles, with no sampling or simplification,
checks the imported names and placements and checks the GLB digest before and
after rendering. The colours aid reading; they do not qualify the materials.
The earlier previews and receipts remain preserved.
The [render receipt](surface-preview-20261011.json) links the sources, the
private image and the unchanged geometry. The PNG stays in the ignored local
delivery.

```sh
python models/917-engine-reconstruction/assembly/render_surfaces.py \
  --delivery work/917-4v-biturbo-20261011/livraison \
  --output work/917-solid-surfaces-20261011/nouveau-rendu
```

## Materials and qualification steps

The [interface check of 12 October](../clearance/README.md) confirms common
volumes between the inherited valves and the cylinder, then proposes a compact
four-valve layout with an 85 mm bore. Its new PicoGK silhouettes remain
separate from this assembly: cylinder head body, seats, guides, ports and
timing must be reconstructed and validated before integration.

The [execution receipt](execution-20261011.json) links the sources and the
results: 67 native definitions checked on both grids, 52 imports checked
without retouching and a GLB of 119 definitions / 1,129 placements. The
maximum error measured when reopening the GLB is below `3 × 10⁻⁸ m`; this is a
numerical transport error, not a physical accuracy.
Four ducts were regenerated after the rejections; the 63 other unchanged
native definitions are reused with a check of their digests.
The correction of the preview after the export changes only the presentation
function; its receipt keeps this distinction and the GLB digest.

The 24 targeted tests pass. The local global check ran 3,638 tests, with 153
skipped and two pre-existing floating-point comparison failures in the
unchanged 993 impeller/stator models. The following `make check` targets are
not reached. The latest corrections to the ducts, poses and preview were
followed by a new targeted verification.

| Family | Candidate route | Missing qualification |
|---|---|---|
| Cylinder heads | CP1 LPBF, treatment and machining of the interfaces | hot material map for the printed batch, fatigue, porosity, walls, depowdering, sealing and metrology |
| Cases, supports, cold ducts | aluminium alloy to be selected, LPBF then machining | preloads, stresses, stiffness, expansion, accessibility and gaskets |
| Pistons | forged and machined 2618 | temperatures, fatigue, skirt, grooves, clearances, crown and balancing |
| Connecting rods | forged and machined Ti-6Al-4V | exact alloy and temper, bolts, fatigue, bearing shell retention, balancing and galvanic isolation |
| Crankshaft, pins, cams | steel to be selected, treatment and grinding | profiles, radii, lubrication, hardness, contacts, fatigue and dynamics |
| Hot manifolds | IN625 candidate, LPBF or conventional manufacturing | thermal cycle resistance, porosity, cracks, welding, flanges and inspection |
| Valves, springs, bearings, retainers, gaskets, electronics | qualified components to buy or to define with a supplier | drawings, tolerances, certificates, loads and service conditions |
| Turbo wheels and shafts | supplier definition or specialised rotor programme | aerodynamics, hot clearances, dynamics, balancing, containment and overspeed |

[EOS describes CP1](https://www.eos.info/metal-solutions/metal-materials/aluminium)
as an aluminium–iron–zirconium alloy for additive manufacturing; this does not
provide an admissible map for our printed cylinder head. For exhaust valves,
[Special Metals describes INCONEL 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf)
for this use: this reference is a supplier lead and qualifies no valve in this
assembly. No mechanical property is invented to produce a safety factor.

Manufacturing will have to follow the
[existing LPBF material contract](../../../twins/reference-917-engine/material-lpbf-qualification-f49.json)
and a professional review, with alloy/batch, machine, parameters,
orientation, supports, treatment, machining allowances, CT/CMM inspection,
pressure tests, corrosion/galvanic effects and fatigue assumptions documented.
Next come hot contacts and clearances, the piston–valve sweep, cam laws, the
real circuits, the thermal/structural calculation, turbo maps and an
instrumented test bench. **Closed shapes and kinematic identities do not
constitute authorisation for metal printing or engine start-up.**
