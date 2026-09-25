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

## First admitted batch

| Component | Size | Mass | Material | Geometry | Assembly |
|---|---|---:|---|---|---|
| `COMP-FUCHS-37024.013` | 7J x 17 ET55, 5x130, bore 71.58 mm | 7.50 kg | forged aluminum | interface proxy | front axle, quantity 2 |
| `COMP-FUCHS-37026.013` | 9J x 17 ET55, 5x130, bore 71.5 mm | 7.95 kg | forged aluminum | interface proxy | rear axle, quantity 2 |
| `COMP-FUCHS-37027.011` | 8J x 18 ET52, 5x130, bore 71.5 mm | 8.20 kg | forged aluminum | interface proxy | front axle, quantity 2 |
| `COMP-FUCHS-37028.011` | 10J x 18 ET65, 5x130, bore 71.5 mm | 8.80 kg | forged aluminum | interface proxy | rear axle, quantity 2 |

Primary source: public documentation from the manufacturer Otto Fuchs. These are
compatible wheels, not Porsche CAD files, nor a claim that they were fitted at
the factory on every variant.

Admitted assemblies: a 30.90 kg 17-inch set and a 34.00 kg 18-inch Carrera set.
The Turbo fitments with spacers remain separate and incomplete.

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
