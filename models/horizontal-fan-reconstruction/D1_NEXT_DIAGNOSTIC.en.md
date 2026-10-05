# After D1: possible causes and proposed discriminating trial

**Update:** the single trial prepared here was authorized and executed.
The [D1C result](D1C_EXECUTION.en.md) passes original numerical criteria but retains
backflow and physical limits. No additional batch was launched.

The [verified private native fields](results/cfd/D1-local-field-diagnostic.json)
allow this lightweight analysis without a new solver. It complements the
[D1 result](D1_EXECUTION.en.md). The control remains unadmitted on pressure;
the strict branch remains incomplete. Field differences do not locate the
pressure equation's algebraic residual.

## Ranked hypotheses

| Priority | Hypothesis | Quantified indicators and scope |
| --- | --- | --- |
| 1 | Nonlinear velocity–pressure update in the blade-tip wake | At 901–920, the strict solver reduces the final residual by a factor of 96.97 and mean local continuity error by 19.40, but the initial maximum changes by +0.174 %. Over the control's 60 iterations, the third correction starts on average at 21.27 % of the first correction's initial residual; some first corrections still exceed the threshold during later updates. Global linearization/correction merits a sensitivity test, without concluding it is the cause. |
| 2 | Nearby-outlet influence in a backflow zone | At 960, net flow is 1.15229968 m³/s and gross backflow 0.12399009 m³/s, or 10.76 % of net flow; 35.15 % of outlet area has inward flux. The ten largest pressure variations remain 31.7–34.1 mm from this outlet, approximately 0.12 D. Proximity and backflow make length sensitivity plausible; they do not prove an incorrect condition. |
| 3 | Mesh conditioning or local resolution | Reproduced metrics match the independent check: non-orthogonality 71.0857°, skewness 1.09927, minimum determinant 0.00515090. The 1 448 cells with \|Δp\| > 1 Pa have maximum non-orthogonality 55.05°, maximum skewness 0.80398 and minimum determinant 0.02393. None overlaps the 69 cells above 65°. The ten maxima have angles 14.9–32.8°. The “worst cells alone” cause is weakened; wake resolution and absent layers remain unqualified. |

The order above represents test priority, not cause probability.
Coarse V2 converges despite maximum non-orthogonality above that of the fine
grid; one global metric therefore does not justify remeshing.

Between 900 and 960, volume-weighted RMS Δp = 0.291515 Pa, maximum = 131.776 Pa;
RMS ΔU = 0.0221393 m/s. Cells above 1 Pa occupy 0.240615 % of volume.
Maxima are at radii 129.3–137.0 mm, z = −15.4 to −17.9 mm, 0.51–2.43 mm from
the nearest rotor-face centroid. These distances are geometric proxies, not
wall distances. Cellular correlation \|Δp\| / \|ΔU\| is 0.487; it proves no causality.

## Condition and flux consistency

Condition types are identical at 900 and 960: rotor `MRFnoSlip` /
pressure `zeroGradient`, housing `noSlip` / pressure `zeroGradient`,
inlet and outlet `pressureInletOutletVelocity`, zero inlet total pressure
and zero outlet static pressure. This configuration does permit observed
backflow. It represents an isolated fan, not measured engine thermal or
hydraulic resistance. Imposed backflow turbulence, engine interfaces and
compressible sensitivity remain to be qualified.

The discrete divergence sum of relative MRF `phi` at 960 is 1.78165×10⁻⁷ m³/s
and matches the sum of **four** patches. The two ports alone have imbalance
1.64016×10⁻⁵ m³/s; relative rotating-face fluxes explain the difference.
This sum is not read as absolute wall leakage. The diagnosis accesses neither
the pressure matrix nor its cellular residual field; it does not claim to
identify cells with the maximum initial residual.

The [official correction code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/applications/modules/incompressibleFluid/correctPressure.C)
shows that `consistent yes` changes the inverse diagonal coefficient and
flux/velocity corrections. The
[geometric-check code](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C)
underlies the three reproduced local metrics; their extrema are compared to
independent results before this report is accepted.

## Smallest proposed trial before launch: one branch

The [fixed protocol](parameters/D1-coupling-proposed-protocol.json) and
[candidate dictionary](parameters/D1-coupling-candidate/fvSolution) change
**only `SIMPLE.consistent no` to `yes`**. The D1 control's 60 complete iterations
are reused rather than recalculated. The candidate branch would start from
the same 900 checkpoint and MPI partition for 901–960. Grid, initial fields,
physics, conditions, schemes, p relaxation = 0.15, relTol = 0.01, absolute
tolerance = 10⁻⁸ and all criteria are identical. Each hash and `uniform`
link is verified before the solver.

Proposed cost: 4 CPU / 5 GiB RAM **and memory+swap**, one branch; approximately
112 s of solver time based on the native control, approximately 180 s total,
**300 s overall ceiling including preparation/reconstruction/audit**, MPI
ceiling 180 s. No third-party service, installation or new access. Launch is
blocked until a window is coordinated; an error or overrun ends the batch
and preserves its receipt, without automatic restart.

The three windows 901–920 / 921–940 / 941–960 are fixed before calculation;
telemetry every iteration and checkpoint at 960. Original criteria remain
mandatory over 941–960: p ≤10⁻⁴, U ≤10⁻⁵, k/ω ≤10⁻⁴, imbalance ≤0.5 %, flow CV
≤1 %, torque CV ≤2 %, direction and complete finite fields.

- A maximum p reduced by at least 30 % relative to the control **and** every
  original criterion satisfied would support coupling sensitivity.
- A change below 10 % over a complete window would not support it.
- Between these bounds or if incomplete: a descriptive result, with no
  invented causal conclusion, extension or admission.

These rules are prospective discrimination criteria, not relaxed admission
thresholds. Even numerical success would not qualify installed flow, cooling,
efficiency or physical oscillation. If this trial is not discriminating, the
next preparation would concern a common outlet length, with documented
CAD/mesh gates and field transfer before any new calculation authorization.

Reproduce lightweight analysis from private local archives:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python source/analyze_d1_local_fields.py PRIVATE_OLD_INPUTS PRIVATE_960_INPUTS PRIVATE_D1_LOGS work/D1-local-field-diagnostic.json
python source/verify_study.py
```

The script launches neither a solver nor a mesh modification and publishes
no complete native field. Archives and scan remain private.
