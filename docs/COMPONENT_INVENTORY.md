# Inventory of the twin's physical components

## Admission rule

A component enters `catalog/components/` only if the following four items are
sourced: size, mass, material and application to the 993. A source must also
identify the part unambiguously.

Geometry is classified separately:

- `interface_proxy`: only the known nominal parameters are represented;
- `envelope`: the external envelope is documented;
- `detailed_solid`: the shape is complete enough for local checks;
- `scan`: acquired geometry, with declared scale and accuracy.

A complete component can join a `logical` assembly even if its 3D transforms are
unknown. It can take part in a spatial check only if its interfaces and their
accuracy are known.

## Admitted components

| Component | Size | Mass | Material | Geometry | Assembly |
|---|---|---:|---|---|---|
| `COMP-FUCHS-37024.013` | 7J x 17 ET55, 5x130, bore 71.58 mm | 7.50 kg | forged aluminum | interface proxy | front axle, quantity 2 |
| `COMP-FUCHS-37026.013` | 9J x 17 ET55, 5x130, bore 71.5 mm | 7.95 kg | forged aluminum | interface proxy | rear axle, quantity 2 |
| `COMP-FUCHS-37027.011` | 8J x 18 ET52, 5x130, bore 71.5 mm | 8.20 kg | forged aluminum | interface proxy | front axle, quantity 2 |
| `COMP-FUCHS-37028.011` | 10J x 18 ET65, 5x130, bore 71.5 mm | 8.80 kg | forged aluminum | interface proxy | rear axle, quantity 2 |
| `COMP-PAUTER-993-230-580-1270F` | 127.0 mm center to center, bores 58.01 / 23.01 mm | 0.535 kg | 4340 steel, shot-peened; forming route not declared | none, inventory only | engine, quantity 6 |

Primary sources: for the wheels, public documentation from the manufacturer
Otto Fuchs; for the connecting rod, the Pauter Machine Company product page,
cross-checked with the TZR Motorsport listing of the same part number. The
wheels are compatible wheels, not Porsche CAD files, nor a claim that they were
fitted at the factory on every variant. The rod is an aftermarket part, not the
original Porsche rod.

Admitted assemblies: a 30.90 kg 17-inch set, a 34.00 kg 18-inch Carrera set and
a 3.21 kg logical set of six Pauter rods, recorded for inventory only. The Turbo
wheel fitments with spacers remain separate and incomplete.

The KBA ECE R124 approvals of the four wheels give a 71.58 mm wheel center bore
and list the vehicle hub as 5/130/71.5. Three records above still carry 71.5 mm
for the wheel; the correction is pending and recorded in the assemblies' known
limits. The approvals also restrict the scope: the 17-inch pair is listed for the
Carrera only with the widened Turbo-Look body, and the 18-inch pair needs the
25 mm rear spacer on the Turbo-Look and Turbo.

The Pauter rod is an aftermarket part, recorded for inventory only: a connecting
rod is a highly loaded engine part, so no geometry or manufacturing file is
produced. Pauter declares its size, its 535 g mass, 4340 steel and the 993 and
993 Turbo application. Whether it is forged or machined from billet is not
declared for this product, and that gap is a recorded limitation. Its logical
set of six weighs 3.21 kg and must not be added to an engine mass that already
contains the rods.

## Mounting relations

An assembly may carry `mounting_relations`. A relation is recorded only when a
source confirms it, and it names the instances, the counterpart (a component or
a named interface such as `front_wheel_hubs_unpositioned`), the fastener and the
tightening torque. A count or a torque that no source gives stays `null`.
`scripts/validate_components.py` checks that every cited source is listed by the
assembly, that a `SRC-` id resolves to `catalog/sources/` with the same URL, that
a record-local source id also defined by a member component names the same URL,
that a fastener count, inferred one fastener per hole, equals a sourced count
parameter of the component, that a torque cites at least one measurement value
and equals it (unit, value, thread, source, and no raw OCR), and that a twin
interface link resolves to a fastener interface whose components include the
derived geometry file of every member (for the wheels, this ties the link to the
axle and the size). An instance is listed once per relation.

First relations: each Fuchs wheel is fastened to its hub with series wheel nuts,
M14x1.5 with a 28 mm spherical collar, at 130 Nm. The wheel approvals give the
nuts and the torque; the workshop manual gives the same torque
(`MNL-TORQUE-0134` front, `MNL-TORQUE-0155` rear, `MNL-TORQUE-0168`). The count
of five nuts per wheel is inferred from the sourced five-hole pattern, one nut
per hole; no source states it directly. No relation
is recorded for the connecting rods: their bolt size and torque are not sourced.
These relations are documentary. They allow no spatial check and are not a
fitting instruction.

The 17-inch Michelin Pilot Sport PS2 N3 tires are candidates well identified by
Porsche and Michelin. They are not admitted yet: the available masses come from
sellers and vary, and the exact material construction of these references is not
given in the manufacturer documents retained.

The first braking batch is also qualified but not admitted. Brembo and ATE
cross-check the dimensions of the Carrera front discs; ATE gives the associated
Porsche part numbers, and Brembo also documents the rear disc. None of the
retained manufacturer documents, however, publishes the net unit mass or a
complete material grade. The details and the exit gate are recorded in
[the German-language braking research](research/phase-2-freinage-allemand.md).

## Acquisition queue

The next batches are researched by subassembly: wheels and tires, braking,
standardized bearings and seals, drivetrain, engine, body, interior. An
incomplete record stays in the source register or in a research issue; it does
not receive a fake default weight or material.
