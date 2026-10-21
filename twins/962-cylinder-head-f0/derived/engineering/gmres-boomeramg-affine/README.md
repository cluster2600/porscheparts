# Actual GMRES/BoomerAMG affine diffusion witness

One authorised MOOSE invocation solved **−Δw=0** in the dimensionless cube
**[1,2]³**, with **w=x+2y+3z** on all six boundaries and a zero initial field.
The 27 HEX8/Q1 cells contain 64 scalar nodes: 56 boundary nodes and eight
genuine interior nodes. Every boundary value is nonzero. Unit diffusivity
is a software coefficient, not a head material property.

The actual run used one Newton step and one GMRES solve with three linear
iterations. Its native KSP report confirms HYPRE BoomerAMG, one V-cycle per
preconditioner application and zero internal tolerance. GMRES kept separate
relative/absolute tolerances of 1e−12/1e−13. The reported automatic strong
threshold was 0.7. Compiled HYPRE support alone was not treated as a pass.

| Complete check | Actual result | Frozen limit |
|---|---:|---:|
| Actual KSP residual ‖Ay−b‖₂/‖b‖₂, assessed from all exported entries | 4.096862444239771e−13 | ≤1e−10 |
| All 64 spatial samples: maximum relative field error | 1.833496317734292e−12 | ≤1e−10 |
| All 64 spatial samples: unweighted relative nodal RMS error | 3.4722931093774176e−13 | ≤1e−10 |
| All 56 boundary samples: maximum absolute error | 5.329070518200751e−15 | ≤1e−10 |
| Identity rows / free rows in the actual 64×64 operator | 56 / 8 | 56 / 8 |
| Free-block relative symmetry defect / actual A–P relative difference | 0 / 0 | each ≤1e−12 |

Each native face flux separately agrees with **(+1,−1,+2,−2,+3,−3)** for
left/right/bottom/top/back/front within the frozen absolute **1e−9** limit.
Independent reconstruction uses all 54 outer Q1 cell-face integrals and the
complete spatial field, rather than net-flux cancellation alone. Root's
independent NumPy review recomputed a relative algebraic residual of
4.0968013307165775e−13 and verified all 64 spatial nodes and six fluxes.
The separate Decimal-50 review found a residual of 4.09677725051261e−13.
Small differences from the binary64 calculations on serialized exports and
the rounded native residual text are retained, within the unchanged limits.

`data/` contains the exact actual numeric A/P, RHS b and Newton correction y,
the final all-node and six-flux CSV files, the native KSP report, final true
residual report and safe exact native log. The correction is the solution of
that KSP system, not an assumed spatial field export. Exactly one complete
block was required in each numeric export. The full constrained operator
has relative symmetry defect **0.09203932417527548** and 128 off-diagonal
Dirichlet-column couplings above the reporting cutoff **1e−12** (152 are
nonzero in the serialized matrix); no full-system symmetry or SPD claim is made.

The complete original artifact/source/runtime hash inventory is retained in
`original-artifact-manifest.json`. Exact safe source/input/protocol snapshots
are under `source-snapshots/`; other preparation records and private commands
are represented by their original hashes and explicit whitelist projections.
Those snapshots preserve their **pre-execution** wording and flags. Separate
authorization, stopped execution, assessment and root review remain distinct
records. In particular, the native receipt's `passed=false` is its stopped
controller ledger; the separate exact `assessment.json` records the scoped
witness pass. The publicly projected contract is not the original contract
and cannot be used as a substitute for its exact frozen digest.

The configured wrapper used a read-only owned runtime and unshared network,
one rank and one OpenMP/BLAS thread, a 30 s soft timeout with 5 s kill grace,
40 s controller wait, systemd RuntimeMaxSec=45, MemoryMax=2 GiB, no swap,
CPUQuota=200% and TasksMax=128. The reaped native-wrapper window was
**0.5160968001000583 s**, return code 0; SSH transport took
**1.2003646660596132 s**. Neither is a head performance benchmark. Actual
peak RSS/CPU usage was not sampled, and no hard output-disk quota is claimed.
No retry, solver installation or shared-runtime modification occurred.

These results establish this installed-runtime **synthetic software witness**.
They do not establish node-to-DOF mapping, equality with an independently
assembled geometric P1 operator, head import, head scalability, mesh/field
convergence, CG/preconditioner SPD, material behavior, CHT, strength, LPBF,
fitment or manufacturing qualification. The native deprecation warning is
preserved; no post-run input change or solver replay was used to remove it.
Original project data/code follows the repository `LICENSE`. No upstream
source or runtime binary is redistributed; primary API/source attribution
and PETSc BSD-2-Clause provenance are in the exact provenance snapshot.

Root and separate retained-output reviews passed within this scope. The
payload is sealed in `receipt.json`; its inventory can be checked without
running a solver:

```sh
python3 - <<'PYVERIFY'
from pathlib import Path
import hashlib, json
base = Path('twins/962-cylinder-head-f0/derived/engineering/gmres-boomeramg-affine')
r = json.loads((base / 'receipt.json').read_text())
for name, digest in r['payload_sha256'].items():
    p = base / name
    assert p.is_file() and not p.is_symlink()
    assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, name
assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(r['payload_sha256']) | {'receipt.json'}
assert r['scoped_synthetic_witness_passed'] is True
assert r['head_execution_credited'] is False
print('Exact payload inventory verified; synthetic software scope preserved.')
PYVERIFY
```

Hash checks do not reproduce native execution or authorise another solver call.
