# M64 — Marangoni predictor contract: native control case passed

**This document keeps the checkpoint of the control case.** The follow-up has
since been run on a fresh copy: [new binary and corrected coupon, incomplete
after 109.55 µs](M64_F58_CORRECTED_COUPON_20260908.md). It requalifies none of
the historical attempts below.

**At this checkpoint, the fix passes only on a native control case of 32 cells.**
The old executable reproduces the `adjustPhi` rejection; the new one clears
the same guard, while keeping the 48 compared tangential tractions.
The [interrupted coupled coupon](M64_F58_COUPLED_FLOW_20260908.md) remains
rejected: its binary was neither modified nor rerun. [Capsule and digests](../../twins/m64-cylinder-head/evidence/f58-predictor-contract-20260908.json).

## Isolated contract defect

The Marangoni condition projects the velocity onto the tangent plane, but
inherits `assignable()=true`. The field `UEqn.H()` has extrapolated
boundaries; `constrainHbyA` reapplies the value of U only for a non-assignable
condition. The normal component of this predictor can therefore escape the
constraint, while the final U is correctly projected.

The tested change is a single method of the Marangoni header:
`assignable() const { return false; }`, as for the native `slip` condition.
The [patch and its digests](../../twins/m64-cylinder-head/source/additivefoam/README.md)
are published to apply the same change to a copy of the pinned sources. The
traction function `snGrad` and projection function `evaluate`, the `noSlip`
and `fixedFluxPressure` conditions, and `adjustPhi`, remain unchanged. The
predictor of the fatal F58 step was not saved: this control case isolates the
contract defect, but does not quantitatively reconstruct that step of the
coupon.

```mermaid
flowchart LR
    A[Native Marangoni BC] --> B[Two binaries: only the contract differs]
    B --> C[Tractions and predictor flux]
    C --> D[Native adjustPhi kept]
    D --> E[Control case accepted]
    E --> F[Full coupon: fix and trial still to do]
```

## History kept

| Attempt | Actual result | Interpretation |
|---|---|---|
| v1 | Compilation rejected, exit 2, 7.130 s | `fvCFD.H` missing; no control case run. |
| v2 | Compilation and `Mesh OK`, exit 134, 58.850 s | Old guard rejected as expected; new one stopped before `adjustPhi` by the "exact zero" oracle. The reader also wrongly expected numeric booleans. |
| v3 | Native pair passed, exit 0, 23.927 s | Old `adjustPhi`: expected exit 1; new: exit 0, domain recognized as closed. |

v3 corrects the oracle and the reader, without retroactively accepting v2. It
reuses the normal velocity budget **already set at 10⁻¹⁴ m/s** by the earlier
BC control case. Each patch must satisfy
`sum(abs(phiHbyA)) ≤ 10⁻¹⁴ × sum(magSf)`, with the area computed natively. The
values must be finite, the norms nonnegative; `ddtCorr` is still required to
be exactly zero on uncoupled boundaries. No flux is overwritten by hand and
the native guard is neither removed nor intercepted.

| Predictor measurement before `adjustPhi` | Old | New |
|---|---:|---:|
| Maximum normal velocity, m/s | 0.10004623 | 6.16298×10⁻³² |
| Sum of boundary flux magnitudes, m³/s | 9.99901×10⁻¹⁰ | 9.75752×10⁻⁴¹ |

The new result is **within budget**, not mathematically equal to zero. The
three temperature gradients tested cover tangential traction, normal gradient
and gradient reversal. The 48 native traction vectors are identical between
the two executables; this is not a comparison between two independent
physical models.

## Scope and evidence

The mesh is stationary; the fabricated state represents a fully liquid phase:
Euler matrix, native upwind convection and diffusion, then `HbyA`, `ddtCorr`
and `adjustPhi`. No PDE is solved, no laser is run. This evidence isolates an
implementation defect, without validating the full flow of the coupon.

OpenFOAM 14, commit `7b05503f98a85be88af930df48623b4d152bfc35`:
[transform contract](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/finiteVolume/fields/fvPatchFields/basic/transform/transformFvPatchField.H#L100),
[slip contract](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/finiteVolume/fields/fvPatchFields/derived/slip/slipFvPatchField.H#L112),
[constrainHbyA](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/finiteVolume/cfdTools/general/constrainHbyA/constrainHbyA.C#L39),
[ddtCorr on boundaries](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/finiteVolume/finiteVolume/ddtSchemes/ddtScheme/ddtScheme.C#L166),
[adjustPhi guard](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/finiteVolume/cfdTools/general/adjustPhi/adjustPhi.C#L82).

The 25 reader tests pass, including the real v2 lines, NaN/Inf, signs,
booleans, falsified bounds and flow or velocity exceedances. The capsule binds
their sources and the native logs. The 19 inputs and six outputs of the v3
return were rehashed; the backend integrity evidence is kept. An independent
cross-reading, without importing the launcher, confirms the digests, the
bounds and the comparisons by direct reading with Decimal. The maximum
traction error observed is 5.10640×10⁻¹² Pa, under the oracle of 10⁻⁹ Pa; this
is not an independent physical validation. The Kali container was deleted,
with no OOM and no timeout: limits of 2 CPUs, 2 GiB memory and combined
memory+swap, 180 s, network disabled. No new Vast rental was used.

**Next step planned at this checkpoint, since executed in the document linked
at the top:** apply only this fix to a new copy of the F58 sources, compile a
new pinned binary, then review a bounded coupled trial with all guards kept.
The 3,300 K cap and the LPBF validation questions remain open; no cylinder
head is validated or authorized for manufacturing by this control case.
