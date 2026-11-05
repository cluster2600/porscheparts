# 935 exact coordinate-origin diagnostic

## Question and upstream admission

The [native geometry and winding audit](../935-native-geometry-admission-20261105/README.md)
finds that every imported face has the correct integer winding relative to
certified positive source tetrahedra. Nevertheless, native floating-point
geometry evaluation reports negative volumes and other defects. This increment
tests whether that evaluation changes under one **exact coordinate translation**.
It does not change surface geometry, connectivity, thresholds, boundary types,
the printing master or the declared physical hypotheses.

The fixed trial origin subtracts `(10,10,10)`, the source lower bound. It is
chosen before native comparison, with no search over origins. A translation
cannot improve intrinsic tetrahedron conditioning or increase the rank of the
uncoupled internal-area stencil. The known stencil rejection and extreme cell
conditioning therefore remain upstream failures even if a numerical warning
changes. No head field solve is admitted by this diagnostic.

## Exactness before native execution

`source/certify_translation.py` binds the final conditioned source volume and
the independently verified native readback by their immutable manifests. For
all 12,543,897 binary64 coordinates, it decodes `x = m * 2^e` and compares the
translated value, scaled by `2^-e`, with the exact integer `m - 10 * 2^-e`.
Every integer lies below `2^53`; conversion cannot conceal integer rounding.
The bounded exponents and finite positive source range are checked first.

All coordinates pass, as does inverse addition of ten. Independent Fraction
controls agree; a one-bit corruption is rejected. A different-origin example
demonstrates that a mathematically rigid transformation can lose source bits,
so exactness is not presumed for arbitrary origins. The predicted translated
point archive is separately reloaded and checked. The exact shape deviation
after the inverse transform is zero. This is stored-coordinate identity, not
physical metrology or confirmation of scan units.

## Native controls and paired protocol

The same content-addressed mesh-CFD image is used on Kali and Vast:
`ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f`.
Its native runtime reports OpenFOAM `13-18870c24d21c`. Actual `transformPoints`
help confirms the positional expression syntax:

```sh
transformPoints 'translate=(-10 -10 -10)' -case CASE
```

Before the head, `run_origin_pair.py` repeats the independently specified
structured cube and its reflected rejection control using the retained native
worker. A five-point precision fixture then requires native identity and
minus-ten transforms to preserve every expected binary64 bit at write precision
17. A deliberately wrong translation is rejected against the fixed prediction.
These actual native controls pass on Kali under a 512 MiB container bound;
all outputs are recovered and verified before owned cleanup.

For the head, the unchanged baseline must finish first with a complete native
report. Failure, timeout or missing terminal content refuses the translated
continuation. Each selected head diagnostic uses native defaults,
`checkMesh -noTopology -allGeometry`, a 600-second deadline and a 48 GiB child
address-space bound. Exit zero alone is insufficient: the full terminal report
and failed-category count are retained. This selector does not complete the
earlier full native topology check.

The translated case is a separate copy. After actual native `transformPoints`,
every one of its 12,543,897 coordinate bits must equal the exact prediction,
and all other native head files must remain byte-identical. Only then may its
geometry diagnostic run. Complete raw logs and tuple-valued metrics are retained;
an absent warning is recorded as absent, never invented as numerical zero.
No invariance tolerance or operator-error bound is established by comparing logs.

## Executed result

Both native head diagnostics complete without timeout: 59.922 seconds for the
unchanged baseline and 60.530 seconds after translation. All 12,543,897 native
coordinate bits match the certified translated prediction; the seven other
native head files remain byte-identical. The baseline repeats the previous
study's reported metric tuples. The selected native check still reports ten
failed categories in **both** frames.

| Native diagnostic | Original frame | Exactly translated frame |
|---|---:|---:|
| Negative computed-volume cells | 4,070 | 3,523 |
| Minimum computed volume | -1.56218e-15 | -3.30701e-15 |
| Face-pyramid warnings | 6,851 | 5,786 |
| Nonorthogonality errors | 1,009 | 962 |
| Highly skew faces | 63,762 | 63,416 |
| Maximum native skewness | 1,112.965 | 3.64923e137 |
| Face decomposition-tet warnings | 288,815 | 288,819 |
| Internal-area determinant below 0.001 | 4,319,287 | 4,319,287 |
| Failed selected check categories | 10 | 10 |

This establishes observable coordinate-frame sensitivity in native numerical
geometry evaluation on this domain. A falling warning count is not a quality
improvement: other values deteriorate severely while the exact shape and
intrinsic conditioning remain unchanged. The prior certified positive source
tetrahedra and complete integer face-winding proof remain authoritative for
stored-coordinate orientation. This comparison does not isolate a particular
native formula or certify its accuracy; it is not a reason to choose an origin
that hides warnings, flip correct face rows or relax admission thresholds.

The complete tuple-valued metrics, raw-log hashes, native transformation
admission and terminal receipts are linked in `results.json`. Both frames remain
rejected for engine physics. The transformed case is a diagnostic copy, not a
replacement geometry or printing master.

Further origin sweeps would not repair intrinsic conditioning. Subsequent
geometry work must address the source-relative poorly conditioned features and
their admissible geometric/topological constraints before another field trial.

## Local capacity and cloud admission

The full Kali profile requires 10 GiB available RAM and 11 GiB free disk before
remote head staging. Its fresh observation finds sufficient RAM but only
10,122,760,192 bytes free disk, below the declared floor. It stops before remote
head staging; the floor is not lowered and no foreign files are removed.
The small native controls already completed independently.

A single receipt-bound Vast attempt is prepared with the same worker, native
mesh, exact translated prediction and pinned dependencies. The complete phase
ledger covers upstream identity, controls, capacity, budget/guard, runtime,
baseline, native transformation/readback, translated diagnostic, verified
recovery, owned deletion and publication. An independent guard is armed and
observed live before the paid launch. First use of the provider's endpoint is
pinned to a dedicated private known-hosts file, followed by strict verification;
this is not independent host attestation. Native SSH uses the existing workload
identity, with Keychain access and agent forwarding disabled.

The original scan is authorized for Vast but this attempt requires only derived
geometry. No scan or derived geometry is sent to an external CAD/AI service.
Supplier inquiries remain unsent.

## Reproducibility and evidence boundaries

Run the exact certificate in a new private directory with the frozen source
volume, parent native capsule and declared output. `run_kali_pair.py` prepares
the actual small-control or paired-head package and its checksummed input
manifest. A package contains `run_origin_pair.py`, the four pinned dependencies,
`parent-native-manifest.json`, `pair-plan.json`, `input-manifest.json`, the
precision fixture/reference and, for the head, `native-head/`,
`translation-proof.json` and `expected-translated-points.npz`.

Execute `python -B run_origin_pair.py` inside that package in the pinned image.
The retained input manifest must be created before execution, not from its
outputs. `recover_origin_outputs.py --root PRIVATE_CLOUD_RECEIPT_DIRECTORY`
requires a terminal worker and private SSH/work receipts. It verifies every
original input and recovers all unique outputs; byte-identical generated copies
are matched to retained owner inputs by hash and size. Resource deletion follows
verified recovery. Raw meshes, native point files and private connection details
remain outside Git.

The original $35 budget remains $30 compute and $5 transfer/closeout reserve.
Prior reservation ceilings are $9.30; this attempt reserves at most $1.50,
giving $10.80 cumulatively. This is not actual spend. Rate-times-duration and
network planning estimates must remain distinct from a provider invoice.
No recharge is requested.

The reconstruction still inherits assumed scale, closures and component cuts,
unknown specimen interfaces/material/loads and an unqualified metal process.
Native frame sensitivity would diagnose numerical evaluation, not qualify CAD,
an engine boundary-value problem, a metal build, finished inspection or engine
service. See `results.json` for the executed outcome and immutable capsule.
