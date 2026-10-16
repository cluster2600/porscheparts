<a id="réplique-962-c-30-l--référence-et-métrologie"></a>

# 3.0 L 962 C replica: reference and metrology

The selected reference is the **3.0 L 962 C with water-cooled heads and
cylinders**. The exact engine type, model year, part numbers and inspection
specimen remain to be selected. Fidelity therefore cannot yet be quantified.
This dossier prepares their acquisition; it provides no Porsche dimensions
and authorizes no manufacturing.

The [Porsche dossier, pages 18–20](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
describes aluminum cylinder/head assemblies welded by electron beam
(“blind cylinders”), gear-driven valvetrain, two camshafts per bank,
tappets and shims, and an independent coolant circuit per bank.
It also describes chamber-volume inspection. This establishes a historical
architecture, not the dimensions of our reference.

The separated assemblies shown by the restorer in the
[existing analysis](ORIGINAL_ARCHITECTURE.md) include declared modifications.
Do not infer a factory detachable interface: establish the welds, repairs and
alterations on the selected specimen. Do not section a historical part to
complete the model. The two spark plugs in the F0/4 L candidates are a modern
proposal; their count and axes are not an OEM definition.
The [M64 interfaces](DONOR_METROLOGY.md) concern a separate conversion and do
not replace this 962 campaign.

<a id="ensemble-de-référence-et-repère"></a>

## Reference assembly and coordinate frame

Acquire matched head/cylinder assemblies, camshaft carrier, valvetrain,
valves, seats/guides, water and oil connections, seals, fasteners and the
corresponding crankcase interfaces. Identify each part, bank and cylinder
position, its part number and condition; keep private identifying numbers
out of Git. Part comparisons must establish any symmetry or interchangeability.

The metrologist establishes a repeatable frame from surfaces, axes and
orientation identified on the actual assembly, then the transformation to the
engine frame. No OEM datum is assumed. Record measurement temperature,
free or assembled condition, fixturing and known tightening conditions.
Separate distortion, wear, repair and original shape; do not rescale a scan
to the hypothetical generator to make deviations artificially small.

<a id="contrôles-à-acquérir"></a>

## Inspections to acquire

| Area | Proposed acquisition and expected result |
|---|---|
| Exterior and assembly | Referenced scan and CMM: envelope, pockets, fillets, planes, registers, every mounting axis and bearing surface; fastener reference and load path |
| Cylinder and chamber | Bore, profile, stack height, combustion deck and chamber surface; volume measured with defined valves and blanking, traceable condition and method |
| Valves and ignition | Every seat/guide axis, angle and position, geometry and interference fit; observed spark-plug count, axis, thread and seat |
| Intake and exhaust | Faces, fasteners, axes, sections and internal port profiles; connections to identified manifolds |
| Camshaft carrier and valvetrain | Planes and bearings, shaft and gear axes, center distances, tappet/shim interfaces and envelopes; timing and clearances documented separately |
| Oil and water | CT if necessary: connections, sections, gallery continuity, thicknesses and unresolved areas; connection to the bank circuits |
| Sealing and thermal condition | Cylinder/head weld, actual seats/seals, surface finishes; establish materials and thermal conditions needed to assess expansion |

CMM: coordinate measuring machine. Define coverage, resolution, calibration
and uncertainty for the intended inspection. For CT, retain reconstruction,
segmentation, artifacts, unresolved areas and accessible independent checks;
voxel size is not accuracy. The metrologist's dossier defines the repeatability
plan and acceptance criteria. No manufacturing tolerance follows from a
single part or measurement uncertainty alone.

The [CSV sheet](replica-measurements.template.csv) is an index to copy under
`work/` for each session. Results are blank; blank means unknown.
Enter exact identity, component, bank, position, inspection, characteristic,
method performed, unit, uncertainty, datums, instrument, calibration and evidence.
Duplicate rows for each axis, seat, port or fastener. Profiles, vectors,
coordinates, repetitions and transformations remain in referenced reports:
a scalar value or a CSV row is insufficient to define them.

<a id="maître-éditable-et-dérivés-de-cylindrée"></a>

## Editable master and displacement derivatives

Reconstruct an editable CAD master of the measured reference: constrained
functional datums, chamber and port surfaces, internal circuits, and cylinder,
camshaft-carrier and crankcase interfaces. Every constraint must point to an
accepted measurement or remain explicitly unknown. Preserve the
[existing studies](FLOW4L_STUDY.md) and their evidence as separate studies.

Before claiming fidelity, produce a deviation map between the master and
independent measurements, with frame, coverage, registration uncertainty,
masked areas and review criteria. Inspect interfaces, chambers and galleries
separately; an attractive exterior does not validate the interior.

Stroke can change displacement without changing the head bore, but requires
checks of piston position at TDC, stack height, clearances, compression and
valvetrain. A bore change requires a separate study of the chamber,
combustion deck, cylinder, thicknesses and cooling. Do not scale the entire
model: historical center distances, fasteners, bearings and connections remain
constrained by the reference unless a change is explicitly identified and reviewed.
Each derivative up to 4.0 L receives its bore/stroke definition, its list of
deviations from the master and its own mechanical, thermal and assembly evidence.

<a id="provenance-et-sortie-de-campagne"></a>

## Provenance and campaign output

Retain authorized access, source owner, measurement and reuse rights,
private locator, digest, date and review decision. Scans, CT, proprietary
drawings and personal data stay out of Git; publish only shareable elements.
The [register](research.json) retains documentary references; a public
photograph grants no reproduction rights.
The expected output is an identified exact reference, reviewed measurements
and an inspected master. [Material qualification](MATERIAL_QUALIFICATION.md),
professional review and physical validations remain necessary afterward.
