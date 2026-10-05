# Outlet position sensitivity: D2 preparation

**Historical preparation: no new mesh or solver had run at this stage.**
[D2 execution and closure](D2_EXECUTION.en.md) are now documented separately.
The [diagnosis](results/cfd/outlet-preparation-diagnostic.json) rereads
SHA-verified private native fields. The [proposed protocol](parameters/outlet-sensitivity-proposed-protocol.json)
fixes assumptions, observables and budget before any execution. At this stage,
[D1C](D1C_EXECUTION.en.md) remained the latest calculation: finer V2 numerically
admitted, outlet and local fields unqualified. Installed dimensions remain unknown.

## Proposed distance and shape

The current outlet is at z = −49.5 mm, maximum radius 138.6 mm: 4542 triangles,
0.0603336 m² and a 156-edge polygon contour. No outlet face owner belongs to MRF,
whose centres span z ≈ ±41.2498 mm. At 960, gross backflow is 0.123990 m³/s;
**87.48% lies at r < 0.6 times outlet radius**. The outer r > 0.75 R annulus
contributes net 1.150090 m³/s. This broad central backflow motivates a substantial
boundary move rather than addressing blade tip clearance alone. No field exists
below the current outlet; neither recirculation closure length nor a physical
minimum extension can be deduced.

The proposed first trial adds **275 mm towards −Z**, one *assumed* rotor diameter,
to z = −324.5 mm. This is a proposed discriminating distance without proof it
suffices. Axial distance from the identified hotspot to the boundary increases
from about 33.6 to 308.6 mm. Section remains the same polygon: no diffuser, radial
widening, automotive plenum or new gap is introduced.

Existing triangles would be extended through **50 prism layers of 5.5 mm**:
227100 new cells, total 680596 against 453496. Spacing remains below the 5.6 mm
overall core target; 40 layers cost less but give 6.875 mm. Algebraic diagnosis
gives an internal determinant proxy minimum 0.380274 for the last layer at
50 levels, above the original 0.001 threshold. **This screening does not replace
checkMesh.** Core points/cells, volumes and connectivity, V2 CAD, physical patches,
rotor and MRF membership must remain unchanged. Former outlet faces become
internal with explicit mapping and −Z orientation; no core interpolation or
renumbering of common cells.

Virtual extension walls use `U slip`, `p/k/omega zeroGradient` and `nut calculated`
on a generic patch. Original housing remains unchanged. This avoids adding duct
friction without measured geometry; confinement and turbulent wake mixing remain
possible. A measured difference would depend on the **domain modeled this way**,
not solely an artificial boundary condition error. Slip is documented in
[Foundation13 code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/finiteVolume/fields/fvPatchFields/derived/slip/slipFvPatchField.H).

The distant outlet retains original conditions: kinematic p fixed at 0,
`U pressureInletOutletVelocity`, k/omega `inletOutlet` with incoming values
0.01 m²/s² and 10 s⁻¹, `nut calculated`. Inlet, 6000 rpm rotation, air
ρ = 1.2 kg/m³, ν = 1.5e−5 m²/s, kOmegaSST, first order schemes, p relaxation
0.15, relTol 0.01 and **SIMPLE.consistent yes** remain identical. Turbulence
values are assumptions without installed measurements.

## Observables in the strictly common core

| Observable | Fixed selection | Statistic and units |
|---|---|---|
| Common Q | Former 4542 faces, `commonOutletFlux` | Oriented sum of phi, positive towards −Z, m³/s; outside MRF |
| Torque and power | Same rotor surface, same origin/Z axis | Total pressure + viscous fluid torque on rotor, N·m; power = −Tz Ω, W |
| Common pressure | 5825 cells at −38 ≤ z < −34 mm, `commonPressureBand` | Volume-weighted mean p × ρ, Pa; same original selection |
| Proximity diagnostics | 4542 outlet owners and 10117 wake cells at r ≥ 120 mm, −22 ≤ z < −10 mm | Local means and differences without physical admission |

Private cell IDs, volumes and selection hashes are retained; common V2
`consistent yes` pressure at 960 is **85.643055 Pa**. This band mean is a control
static pressure, not port pressure rise. Comparing p = 0 at the former boundary
directly with internal p after extension would conflate different statistics.
p is a static scalar in both regions; flow uses only the common face outside MRF.

The [functionObjects fragment](parameters/outlet-common-functionObjects.dict)
prepares writing every iteration. `surfaceFieldValue/orientedSum(phi)` respects
faceZone flipMap; [official code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/fieldValues/surfaceFieldValue/surfaceFieldValue.H)
states that volume fields are not interpolated on its internal faces. Pressure
therefore uses `volFieldValue/volAverage` on a fixed cellZone, following
[official code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/fieldValues/volFieldValue/volFieldValue.H).
The fragment does not create zones and had not yet been tested in a new case.

## Local difference of 317.7 Pa: what fields actually show

The compared 960 fields have **the same domain** and start at the same 900 state;
only `consistent` coupling changes. Cell 288831, volume 0.712311 mm³, lies at
(46.230; 124.591; −15.887) mm, r = 132.892 mm. Distance to the nearest rotor
face centroid is about 0.509 mm: a geometry proxy, not exact surface distance.
Its pressure changes from −1248.215 Pa at 900 to −1340.396 Pa in the control and
−1022.727 Pa in D1C: opposite changes −92.181 and +225.488 Pa arithmetically explain
the **317.669 Pa difference**. ΔU is 6.820 m/s in this cell; maximum elsewhere
reaches 67.665 m/s.

Global volume-weighted Δp RMS is only 0.544038 Pa and the cell-count 99th
percentile is 0.216176 Pa. However, 12 cells exceeding 100 Pa represent
0.0006963% of volume and contribute 52.05% of weighted squared difference.
Band z ∈ [−20; −15] mm concentrates the hotspot; at the outlet
z ∈ [−49.5; −45] mm the maximum is 8.096 Pa. Stable integrals thus hide strong
local sensitivity. This does not locate algebraic residuals, prove physical
oscillation or establish outlet causality. Future checks must retain RMS,
percentiles and maxima, including the wake, even if integrated observables pass.

## Short protocol and gate interpretation

1. Prepare appended prisms and explicit mappings; retain four-rank MPI core
   ownership and assign columns to their original face owner rank. Verify
   CAD/core/MRF identity, common zones and orientation. Require **independent
   standard and extended checkMesh**, zero failures and original thresholds
   before any solver. Stop if preparation fails; no threshold relaxation or rotor
   remeshing in this batch.
2. Restart **two sequential cases of 60 iterations 961–1020** from the same
   private D1C/960 `consistent yes` state: current then distant outlet. Retained
   control 900–960 does not replace the new control. Initial core is identical;
   added columns initialize from outlet values/flux, with recipe and hashes
   recorded before starting. Added numerical transient may exhaust the budget.
   Measure every iteration, save 980/1000/1020, no automatic continuation.
3. Require **ten original numerical criteria**, twenty consecutive measurements
   1001–1020 and finite/complete fields for the actual cell count. Add prospective
   steadiness checks: common pressure standard deviation ≤ 2 Pa; between last
   two windows ΔQ ≤ 1%, ΔT ≤ 2%, Δpressure ≤ 2 Pa; between checkpoints1000/1020,
   volume-weighted core RMS Δp ≤ 1 Pa and ΔU ≤ 0.1 m/s. Publish local maxima as
   unqualified. Matrix residuals normalized on different domain sizes do not
   directly measure a physical domain effect.
4. **Only if both cases pass**, compare means over1001–1020:
   |ΔQ|/max(|Qa|,|Qb|) ≤ 1%, |ΔT|/max(|Ta|,|Tb|) ≤ 2%, likewise power;
   |Δcommon pressure| ≤ max(5 Pa, 1% of the maximum of both absolute values).
   Division by zero is expressly undefined. These analyst-declared screening
   thresholds are neither Porsche tolerances nor experimental validation.
   Numerical failure: **inconclusive** comparison. Numerical pass but differences
   outside bands: **model operating point depends on domain**. Pass: only these
   integrals have low sensitivity to **this extension**; no general independence,
   airflow improvement, local convergence or installed cooling validation.

## Proposed budget and outstanding prerequisites

D1C used 117.182 s solver time for 60 iterations; cell ratio 1.501 estimates
about 175.87 s for the extended branch, without guaranteeing conditioning.
Proposal: **4 CPU, RAM + swap capped at 5 GiB, no network, 8–10 nominal minutes,
720 s maximum** for the complete execution. Subcaps: append and gates 120 s,
control solver 180 s, extended solver 300 s, preparation/reconstruction/audit/
archiving 120 s. Global deadline dominates, stopping without retry. This excludes
prior development of the mesher and runner, **not yet implemented at this stage**.
Proposed memory is a limit and estimate, not an aggregate measurement of a future
case.

Prerequisites: verifiable append recipe and runner, independent new-mesh gates,
audited startup and field mappings, correct reading of four new functionObjects,
actually free resources and coordination before launch. This preparation commits
no future solver. Raw scan, complete fields and native selections remain private.

Reproducible solver-free verification: `make fan-program-check`. The
[diagnostic command](source/diagnose_outlet_preparation.py) accepts five private
paths: control960, extracted D1C archive, history900, JSON report and private NPZ
selection. It rejects inputs differing from native manifests; complete
reproduction requires those private inputs.
