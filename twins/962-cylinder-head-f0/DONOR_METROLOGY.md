<a id="kit-962--campagne-dinterfaces-du-donneur-gate-g1"></a>

# 962 kit: donor-interface campaign, gate G1

**Confirmed target: 1,000 metric horsepower at the crankshaft, bench then track.**
The donor remains to be identified; the M64/60 is a candidate, not a selection.
This dossier prepares measurement. It contains no new Porsche dimensions.

The [existing M64 contract](../m64-cylinder-head/interface-contract.json) and its
[documentary validator](../m64-cylinder-head/validate_interface_contract.py)
remain the references for M64 interfaces. Their October 12, 2026 check leaves
eight critical interfaces incomplete, the variant unselected and four
qualification evidence items absent. The [962 F0 contract](interface-contract.json)
describes another reference: its hypothetical dimensions must not be
transferred to the donor.

<a id="pièces-et-repères-avant-la-mesure"></a>

## Parts and datums before measurement

Identify the exact engine type, model year, bank, cylinder position,
case/cylinder/head/camshaft-carrier part numbers and existing modifications.
Keep personal identifiers and vehicle numbers out of Git.
Cross-check the part numbers with the [M64 documentary register](../../docs/reports/M64_INTERFACE_SOURCE_REGISTER.md).
A 964 Turbo 3.3 must not be treated as a Turbo 3.6 M64.

Provide a matched case/cylinder/head/camshaft-carrier assembly, plus the
corresponding seals and valvetrain parts. Document condition, wear, repairs
and disassembly; a worn-part measurement is not a manufacturing tolerance.
Measure each part/bank before concluding symmetry or interchangeability.

The metrologist must define a repeatable frame: reference surface,
register/cylinder axis and orientation defined by an identified feature.
These are **datums to establish**, not known OEM datums.
Record the transformation to the assembly frame and measurement temperature.
Do not visually align the scan to F0.

<a id="feuille-de-mesure-et-méthode"></a>

## Measurement sheet and method

The [CSV sheet](donor-measurements.template.csv) indexes inspections and is
to be copied under `work/` for each part/session. Result fields are blank.
Duplicate each row for every stud, axis, port, cylinder or point actually
inspected; `feature_instance` must remove ambiguity.
Record raw repetitions in `raw_evidence_ref`, not only an average.
Declare unit, instrument, calibration, method, uncertainty and review status.
A blank cell remains unknown, never zero.

| Interface family | Proposed acquisition | Required deliverable |
|---|---|---|
| Studs and mounting | CMM on matched case, cylinder and head | Every axis and position in the frame, thread/engagement, bearing faces; stud part number |
| Register and combustion deck | Bore gauge/CMM, depth and profile | Diameters, depth, seat, groove/seal, form and surface finish |
| Camshaft carrier/valvetrain | CMM and assembly measurements | Axes, center distances, bearings, planes, chain/gear entry, oil path and envelope |
| Oil | External measurements, then CT if the interior is inaccessible | Supply/return positions, sections and connections; no flow inferred from a diameter |
| Intake/exhaust | CMM, seals and referenced scan | Axes, faces, fasteners, envelopes and port sections |
| Seats/guides/spark plugs | Reference metrology, then supplier drawing | Axes and interference fits of the 2V part; new 4V/twin-ignition axes to design separately |

CMM means coordinate measuring machine. Instrument selection and uncertainty
must suit the required tolerances. A caliper can check scale; it does not
replace axis measurements. At least three independent setups per critical
dimension provide an initial repeatability check, without determining
uncertainty on their own.

The engine builder/designer must establish functional dimensioning and the
new drawing's tolerances: do not use measurement uncertainty as a tolerance
or reconstruct a tolerance from a single donor.

<a id="ct-et-raccordement-au-jumeau"></a>

## CT and connection to the twin

If CT is necessary, request assessed coverage, resolution and uncertainty,
segmentation, native data and surfaces, with explicit reuse rights.
Compare at least three independently measured accessible features distributed
through the volume; voxel size does not prove accuracy.
Record artifacts, unresolved surfaces and installed orientation.
CT of a 2V head documents its original interfaces and passages, not the
feasibility of a new 4V chamber and its coolant circuit.

Keep raw scans and reports in an authorized private location. Publish only
shareable results, locators, digests and decisions.
The [existing measurement-record template](../../catalog/templates/measurement-record.json)
can serve scalar dimensions after replacing **all** its examples.
Coordinates, axes, profiles and registration uncertainties require a specific
metrology report; the CSV alone does not validate them.

For the bottom end, complete stack height, piston position at TDC,
crankcase registers and cylinder pitch. The review of crankcase retention
also requires bearings, load-bearing sections, stud attachments, the exact
crankshaft/rods/pistons and inspected condition. The head sheet alone is not
a bottom-end strength dossier.

An accepted acquisition feeds the **exact donor's** contract, then a new
constrained model inspected independently. The F0 generator and its digests
remain preserved. The load path to verify is chamber/combustion deck →
cylinder and mounting → case, including preload and expansion effects;
tightening torque alone does not establish preload.

<a id="sortie-de-g1"></a>

## G1 output

G1 requires donor identity, reviewed interfaces with sources and tolerances,
a common frame, explicit incompatibilities and a bottom-end retention decision.
Combustion loads, temperatures, preload and service life must be supplied
for mechanical review; 1,000 metric horsepower does not define them.
Completing a sheet or passing the documentary validator authorizes neither
manufacturing nor engine testing. [Material qualification](MATERIAL_QUALIFICATION.md)
and the subsequent [program](KIT_962_PROGRAMME.md) gates remain open.

This dossier sends no request to a laboratory and orders no part or CT.
Donor selection and access remain to be confirmed.
