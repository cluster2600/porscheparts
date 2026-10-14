# Weight and original-fastener correction

12 October 2026. **The 2.108 kg / 20 mm plate is rejected. No replacement is
accepted from the three lighter studies in this review.** They meet the 1.2 kg
nominal mass ceiling but still have excessive computed flexibility and unresolved
high elastic stress demands. This is a completed provisional screening campaign,
not a released part or a prediction of physical failure load.

## Corrected brief

- Target: **at most 1.0 kg**; fallback absolute ceiling: **1.2 kg**. This covers
  the finished carrier alone, excluding the separate bracket, mountings and bolts.
- Retain the original fasteners and joint stack. PET lists four M10 × 20 central
  bolts; making the carrier pad alone 20 mm consumes their nominal under-head
  length before accommodating the bracket and nut. That was a design error.
- Preserve mounting axes, bolt seats, the mating face and tool access. Measured
  OEM pad thickness, available bolt grip, thread engagement, bolt grade and vehicle
  clearances remain **unknown**. The previous 8 mm pad was never an OEM measurement.
- Obtain stiffness through the section shape and local load paths within the mass
  budget. Passing a volume/mass check is insufficient to select a design.

Assembly evidence remains in the [PET requirements](../pet-redo/requirements.json).
The load path is engine → separate bracket → four M10 joints → carrier → two
mountings → body, with the gearbox support affecting load sharing.

## Geometry actually generated

[CAD generator](cad.py), [V3 inputs](study-v3.json), [V4 inputs](study-v4.json),
[V5 inputs](study-v5.json), [independent study comparison](check_lightweight.py),
[solver](simulate.py), [rendering](render.py) and
[machine-readable results](lightweight-results.json) are retained.

| Study | Nominal dense Ti mass | Change | Disposition |
| --- | ---: | --- | --- |
| V3 | 0.998 kg | 28 mm deep hollow arms, 2 mm skins/webs, original large windows, flat 8 mm centre | Mass target reached by only 2 g; structural screen rejected |
| V4 | 1.167 kg | 32 mm hollow arms; smaller windows; flat 8 mm centre | Below fallback ceiling; structural screen rejected |
| V5 | 1.185 kg | Curved rear ribs around central openings; original assumed bolt seats remain 8 mm | Below ceiling by 15 g; structural screen rejected |

All three export one valid STEP solid and one closed STL component. The 2 mm
wall values are design inputs, not a qualified manufacturing minimum. V5 adds
reinforcement behind the assumed mating face: its maximum Z is +24 mm while
the end eyes extend to −16 mm. This 40 mm overall depth needs vehicle-clearance
measurement; a mass-compliant solid is not evidence that it fits the engine bay.

Material remains the [TIMET dense Ti-6Al-4V elastic reference](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf)
at 4.42 g/cm³ and E = 107 GPa. No porosity credit, alloy/process qualification,
manufacturing tolerance budget, yield allowable or fatigue curve is assumed.

## What the interface check establishes

The checker reads the exported STEP, independently recomputes mass, and compares
protected regions with the frozen **assumed V1** STEP, SHA-256
`b217328fc28fa1d517e9c771348b31b3f790612d25e8771eba7e4e2445316159`.
The protected regions are the front central mating face, four 25 mm diameter
bolt-seat/access columns, the two large central openings, both end bores and the
four end seating faces. Symmetric differences are zero for V3, V4 and V5. Eight
assumed axial tool columns are clear. Their 12.5 mm radius is not a measured socket.

The first checker protected the entire flat centre. V5 legitimately adds material
behind that face, outside the protected bolt columns; the final check preserves
the actual study joint regions rather than prohibiting all central reinforcement.
Earlier checker receipts are retained separately. A deliberately thickened bolt
seat fails the final check; V2 fails the independent 1.2 kg mass gate. An initial
V5 attempt at 1.202 kg was also rejected before export and simulation.

These are **regression checks against assumed geometry**. The independent OEM
interface contract remains unverified; original-fastener compatibility is not
established by them.

## New calculations on these solids

Eleven new CalculiX 2.21 jobs used the same explicit screening scenario as the
earlier study: **4,000 N in −Z plus 850 Nm about Y**. This is not a measured load
on the user's Turbo or a 700 hp rating. Supports were fixed end bores or springs
of 1,000 N/mm per eye per direction. Bolts, preload, friction and contact are not
represented by the equivalent bore loading.

The table uses the finer mesh for each variant. Stress values are peak elastic
integration-point demands; the large responses make them unsuitable as physical
predictions without nonlinear material/joint models.

| Study | Fixed-end displacement | Spring-support displacement | Fixed / spring peak stress |
| --- | ---: | ---: | ---: |
| V3 | 6.728 mm | 47.284 mm | 2,806 / 7,267 MPa |
| V4 | 4.592 mm | 42.583 mm | 1,227 / 2,600 MPa |
| V5 | 3.913 mm | 23.143 mm | 1,034 / 2,002 MPa |

V3 concentrates stress at the outer arm openings. V4 also exposes the flexible
flat centre and end transitions. V5 improves the centre but does not solve the
structural problem. It is rejected as a next-stage candidate despite meeting the
fallback mass ceiling. No agreed allowable displacement or qualified strength
value exists; this is a screening decision, not a certified pass/fail margin.

V5 refinement from 37,824 to 81,361 C3D10 elements changes fixed-end displacement
by 2.27% and peak stress by 5.03%; the spring case changes by 1.94% and 5.38%.
Further stress convergence has not been established. All accepted meshes have
positive sampled Jacobians. The finest V5 mesh volume differs from CAD by −0.0134%.

New fatigue life, buckling, modal and manufacturing-distortion studies were not
run on these rejected candidates. Results from the older 20 mm solid are not
transferred to them. The next meaningful design inputs are the measured original
joint stack and installation envelope, calibrated support/load sharing, and the
chosen material/process properties; the mass and unchanged-fastener requirements
remain fixed.

## Verification and retained files

The analytical unit-cube check passed on the current native ARM solver. Its
binary SHA-256 is `271f8411371b978d7a8d31a7a13d0765e6e1f872e8a8b1d6aac6d0856c71ec6c`.
Five numerical-bookkeeping tests and four existing carrier tests passed. Rebuilding
V1 with the modified generator reproduces its STL byte-for-byte. All 11 solver
input/mesh hashes and their STEP associations were checked. Catalogue validation
and the targeted page/link checks passed. The full `make check` was not repeated;
the preceding campaign stopped at an unavailable nested-Docker target after its
Python suite passed. No merge or release is proposed here.

Local outputs are under `work/carrier-bionic-lightweight-20261012/`: each variant
has editable STEP, STL, CAD views, geometry/constraint receipts, meshes and raw
solver outputs. V5 also has field plots. `summary.json`, `results.csv`, the solver
archive and `sha256.json` retain the campaign. The original V1/V2 outputs and
their frozen manifest remain intact. The images render actual CAD with a depth
buffer; the cutaway is explicitly labelled. Python dependencies are the existing
build123d/OCP, Gmsh, NumPy, matplotlib, trimesh, PyVista and VTK installations.

Reproduce a geometry check using the existing CAD environment:

```sh
python cad.py study-v5.json /absolute/path/new-v5
python check_lightweight.py /absolute/path/new-v5 /absolute/path/frozen-v1/carrier.step
python render.py /absolute/path/new-v5
python simulate.py /absolute/path/new-v5 --mesh 6
CARRIER_STUDY_CONTAINER=<prepared-native-calculix-container> python simulate.py /absolute/path/new-v5/mesh-6
CARRIER_STUDY_CONTAINER=<prepared-native-calculix-container> python simulate.py /absolute/path/new-v5/mesh-6 --support 1000
```
