<a id="culasse-962-c--référence-fidèle-et-famille-de-30-à-40-l"></a>

# 962 C cylinder head: faithful reference and 3.0–4.0 L family

**Research continuation:** [published family dimensions](DIMENSIONAL_BASIS.md)
have been found. The owner requests continued work with explicit assumptions
for missing dimensions; the [bionic family](BIONIC_FAMILY.md) carries this
geometry continuation. The `null` fields in the register below concern the
exact unmeasured physical reference; they do not block these design candidates.

**Decision of October 16, 2026: use the water-cooled 3.0 L 962 C as the
reference, reconstruct its head as faithfully as possible, then study several
displacements up to 4.0 L.** The [register](replica-family.json) carries this
new priority. The bionic models and the [Mezger 4 L SP95 scenario](MEZGER_4L_SP95_EN.md)
remain derivative studies; they do not define the original geometry.

This delivery provides a reference definition, a target range and a displacement
calculator. **No measured replica CAD is available yet.** This change does
not turn the previous STL files into replicas.

<a id="référence-historique-et-niveau-de-preuve"></a>

## Historical reference and evidence level

The [Porsche “40 Years Group C” dossier](https://newsroom.porsche.com/dam/jcr:a6f33b52-c47d-47b4-98c1-7e963661f587/40%2520Years%2520Group%2520C.pdf)
documents the fully water-cooled four-valve 3.0 L at the 1985 Le Mans practice
sessions (page 8), the 2,994 cm³ types 935/79, /82 and /83, and the
3,164 cm³ types /79 and /86 (page 18). This identifies a family; the type,
year and physical reference to copy remain to be identified.

Pages 19–20 describe aluminum cylinder/head assemblies welded by electron
beam, Nikasil bores, two gear-driven camshafts per bank, shimmed tappets
and two independent coolant circuits with one pump per bank.
Confirm the precise construction on the selected specimen before designing
its connection.

**The 3.0 L donor's bore/stroke remains unknown.** The dossier's
92.3 × 66 mm pair concerns the 956 935/76; it will not be transferred to the
962 C. The frequently cited 95 × 70.4 mm pair is not confirmed here by a
primary source for the donor. The spark-plug count also remains to be
established. The [photographs already examined](ORIGINAL_ARCHITECTURE.md)
show a central opening and an assembly modified by the restorer; they prove
neither a dimension nor the complete factory specification.

<a id="gamme-de-travail"></a>

## Working range

| Designation | Displacement used | Status |
| --- | ---: | --- |
| 3.0 L reference | 2,994 cm³ | Selected historical Porsche family |
| 3.2 L period context | 3,164 cm³ | Documented historical variant; shared head not proven |
| 3.4 L | 3,400 cm³ | Proposed derivative target |
| 3.6 L | 3,600 cm³ | Proposed derivative target |
| 3.8 L | 3,800 cm³ | Proposed derivative target |
| 4.0 L | 4,000 cm³ | Requested family ceiling |

The intermediate steps are a proposed range, not approved engine recipes.
Bore, stroke, compression ratio, pistons, valves and available components
remain to be selected. The calculator also accepts intermediate targets in
the 2,994–4,000 cm³ interval.

The previous **102 × 81.6 mm scenario gives 4,000.660 cm³**. Its sources and
evidence are preserved; it does not strictly meet the new 4,000 cm³ ceiling.
At a hypothetical 102 mm bore, the calculation gives a stroke of approximately
81.58654 mm for exactly 4,000 cm³. This algebraic result does not select a
crankshaft and is not a manufacturing dimension.

<a id="ce-qui-reste-commun-et-ce-qui-doit-être-revu"></a>

## What remains common and what requires review

The historical master must preserve the surfaces, axes, valvetrain,
interfaces, oil circuit and water topology actually measured. The
[962 C metrology dossier](REPLICA_METROLOGY.md) prepares this acquisition;
the existing M64 dossier concerns another base. No global scale factor is
applied to the head, studs, threads or camshaft carrier.

A **stroke change at constant bore** does not directly change chamber
diameter. It requires checks of block/cylinder height, compression, piston
shape, piston/head and piston/valve clearances, valvetrain kinematics, loads
and cooling. It therefore does not guarantee head reuse.

A **bore change** requires revisiting the chamber, cylinder/head seat or
connection, seats and valve clearance, thicknesses, center distances and load
paths. Water, oil and valvetrain must then be checked on every assembly.
We cannot yet promise one head body for the entire range or claim that a
102 mm bore fits in the crankcase.

Twin ignition, BCC ribs, conformal galleries and LPBF materials remain
derivative choices to justify separately. They will not be added to the
historical master without original-specification evidence. The previous
1,000 PS and SP95 targets do not become replica specifications or a promise
for every displacement.

<a id="reproduction-du-calcul"></a>

## Reproducing the calculation

`V = π × bore² × stroke × 6 / (4 × 1000)`, with lengths in mm and
displacement in cm³. Displacement alone does not determine both lengths.
The default report therefore leaves them at `null`. An explicitly supplied
length becomes an assumption; the other is only calculated.

```sh
python3 twins/962-cylinder-head-f0/source/displacement_family.py
python3 twins/962-cylinder-head-f0/source/displacement_family.py --check
python3 twins/962-cylinder-head-f0/source/displacement_family.py --target-cm3 4000 --bore-mm 102
python3 -m unittest discover -s tests -p 'test_962*.py' -v
```

The [retained report](derived/replica-family-report.json) is linked to the
register and calculator by their digests. This tool performs no PicoGK
invocation, STEP/STL export, solver run or purchase. Its outputs qualify
neither compatibility, power, manufacturing nor sale.

The next input needed to reconstruct the shape is an identified 962 C
assembly, with measurement rights, matched head/cylinder and camshaft carrier,
then exterior metrology, gallery CT and interface measurements.
The register's unknowns remain `null` until evidence is received.

<a id="vérification-du-16-octobre-2026"></a>

## Verification on October 16, 2026

The 53 targeted 962 tests finish without failure: 48 pass and 5 are skipped
because VTK is unavailable in the Python 3.12 environment used.
The eight new tests check units, both calculation directions, bounds and
invalid inputs, preservation of unknowns, the report, program links and the
blank metrology sheet. The old models' digests pass their checks; their
geometry is unchanged. Report reproduction and the strict link check pass.

The global `make check` runs 4,040 tests in 267.189 s: three failures and
230 skipped tests. Two exact floating-point equality failures concern
unmodified 993 fan modules; the same differences appear in the previous
study's log. The third concerns two local Python caches in the OpenFOAM
benchmark. These caches created during verification are removed; the
17 benchmark tests pass again with `PYTHONDONTWRITEBYTECODE=1`.
The other `make check` targets pass separately with `make -o test check`.
This does not turn the initial `make check` result into an overall success.

Local logs are retained under `work/962-replica/`. No new CFD/CHT calculation,
native replica export, physical test, remote CI or merge is claimed for this
local delivery.
