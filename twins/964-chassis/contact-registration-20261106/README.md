# Source-contact registration and USD runtime review

Date: 6 November 2026. Status: **diagnostic progress; no registered interfaces or
validated replacement cell**. The [full-goal ledger](goal-ledger.json) preserves
the engineering, mould, manufacturing, road/track and native Omniverse work.
The programme's 1200 kg value is a vehicle input, not a shell mass or load case.

## Source contacts and the observed scan

The [owner archive review](../owner-frame-data-20261105/README.md) admitted
57 documentary entries. It did not register the scan. This review makes the
next source-to-scan check explicit in an independent
[correspondence contract](correspondence-contract.json).

Mi F/G describe four 25 × 34 mm aperture centres at two longitudinal stations.
Their nominal transverse spans are 1330 and 1236 mm; same-side and cross-body
distances are 1245.893254 and 1787.772357 mm. All four points are coplanar.
Source uncertainty and scan localisation uncertainty remain unknown. A future
fit needs positively observed contacts, physical front/rear/side/up context,
defined aperture-mouth planes and independent off-plane checks. A numerical
distance match alone cannot supply these observations.

[extract_candidates.py](extract_candidates.py) checks the original vertex and
open-edge hashes, preserves every original boundary component ID set, and
replays the fixed exploratory size screen. [screen.py](screen.py) derives the
F/G network from the pinned source record, requires the ID archive hash bound
by the extractor, recomputes candidate centroids from original IDs and checks
all six interpoint distances. A separate scalar
distance table and combination-first enumeration verify the numerical result.
Neither script admits physical contacts or produces a transform.

The [observed result](observed-result.json) records:

| Check | Observed result |
|---|---|
| Original open edges / components | 118,411 / 1,521; all simple cycles |
| Prior candidate replay | All 255 retained rows and original ID sets match exactly |
| Broad nominal-size subset | 23 contours |
| Ordered four-contour assignments | 212,520 |
| Assignments with every edge within the fixed 100 mm diagnostic bound | 0 |
| Minimum six-edge RMS discrepancy | 159.875572 mm |
| Minimum worst-edge discrepancy | 249.616218 mm |
| Physical correspondences admitted / donor transform | 0 / none |

The broad size and 100 mm settings are search/rejection settings, not scanner
uncertainty or engineering acceptance tolerances. This rejects **only this
fixed subset** as a complete F/G registration. It does not prove that the
features are absent from the complete scan. Open scan loops may be acquisition
gaps rather than physical apertures; plugs, pads, covers and mechanical parts
must not be substituted for fixed-body contacts. Existing cropped inspection
windows can exclude relevant structure, so future identification must retain
the full original context.

## Reproduce the private scan diagnostic

Use Python 3.12 with NumPy and SciPy, from the repository root. The original
private arrays must already be present at the paths below. The scripts refuse
changed inputs and existing output directories. Change the run suffix for a
new attempt; do not overwrite retained evidence.

Run this Python block with that interpreter:

```python
import hashlib
from pathlib import Path
import subprocess
import sys

folder = Path('twins/964-chassis/contact-registration-20261106')
base = Path('work/964-registration-replay-new')
vertices = Path('work/964-model-year-review-20261029/replay-001/verts_vehicle.npy')
edges = Path('work/964-observed-boundaries-20261029/review-001/source_open_edges.npz')
source = Path('twins/964-chassis/owner-frame-data-20261105/source-data.json')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

subprocess.run([sys.executable, str(folder / 'extract_candidates.py'),
    '--vertices', str(vertices), '--vertices-sha256',
    '201787314680bcd60fb5f9b8910e28b0025d60c380dc77fa458a41bb17942bc9',
    '--source-open-edges', str(edges), '--edges-sha256',
    '22fa12246c7bce2f092d370d77208f317761a74af4b525eeb75afcf11d4618c2',
    '--output', str(base / 'extract')], check=True)
audit = base / 'extract/audit.json'
ids = base / 'extract/candidate-source-ids.npz'
subprocess.run([sys.executable, str(folder / 'screen.py'),
    '--source-data', str(source), '--source-sha256',
    '562b27859d7e717179b4d60f5dd501fd7641107f4180b50fdd17647596045a15',
    '--audit', str(audit), '--audit-sha256', sha(audit),
    '--candidate-ids', str(ids), '--candidate-ids-sha256', sha(ids),
    '--vertices', str(vertices), '--output', str(base / 'screen')], check=True)
```

The hashes calculated between stages identify the newly generated private
derivatives. Admission still depends on the pinned original inputs and fixed
extraction code/settings. Raw arrays, component coordinates, ID archives and
source-document pages stay outside Git.

Eleven focused controls cover correct rigid-motion patterns with decoys,
width-only false matches, coplanar reflection ambiguity, altered contact
definitions, missing/foreign/reassigned IDs, changed metrics, invalid boundary
topology, same-centroid ID substitution and hash rejection before output:

```sh
python3 -m unittest discover -s tests -p test_964_contact_registration.py -v
```

## Executed USD checks and native runtime limits

The [runtime receipt](runtime-receipt.json) and
[CPU replay instructions](runtime-replay.md) record real execution in a bounded
Linux arm64 container on Mac Docker. The pinned environment includes
USDExchange 2.3.0, OpenUSD 25.5, AssetValidator 1.18.0 and SimReadyValidate
2026.4.8. This installation did not modify the host's separate OpenUSD 25.11
environment. A later live check found its cached base interpreter missing and
the default Foundation checkout empty. A fresh isolated checkout restored the
pinned Foundation dependency, and the Docker validation/witness path executed
again successfully. Host Python availability remains separate from this
working Linux CPU path.

The Linux preflight is ready. A synthetic cube passes minimum USD and the
explicitly narrow metadata rule. The validators also execute on the
**historical rejected whole-body scene**: minimum USD passes, AssetValidator
reports eight failures and six warnings, and the generic
`Prop-Robotics-Neutral` diagnostic reports eight failed requirement instances.
That profile is not an automotive engineering acceptance specification.
Missing normals, untyped groups and other findings remain recorded; no
material, density, laminate, collision or mass assignment was attempted.

This runtime result establishes an executable CPU validation path. It does not
repair or reinstate the rejected geometry. The Mac renderer still lacks
`ovrtx`; the cached Linux Kit binary cannot execute on this Mac; the checked
Kali1 GPU is Intel. No new native RTX image or Kit viewport was captured.
The final admitted package still needs its own applicable validators and a
complete native Omniverse review, including framing/interior views, component
selection, save/reopen, reconnect and source-hash preservation.

## Media and next engineering work

Two current private images, `whole-body-candidate-locations.png` and
`regional-source-context.png`, show whole-body and regional scan diagnostics.
Their hashes and captions are in the observed result. They are Matplotlib
projections of observed scan data, not photographs or Omniverse application
screenshots. They stay private because source publication rights are not
established. Historical rejected-scene renders do not fulfil final-cell media.

The next geometry step is independent identification of original body contacts
with the contract's local rim/assembly evidence, followed by uncertainty and
holdout checks. Hidden tunnel/upper-cell surfaces, variant-specific interfaces,
reference-body correlation, complete loads, laminate/core/adhesive/insert
properties, mould/process simulation and professional review remain open in
the ledger. No structurally qualified cell or mould is released by this review.

The previously approved TetraVision enquiry has no reply in the narrowly
checked thread/sender search. The owner declined sending the
[Autorobot enquiry](autorobot-request.md); it remains an unsent draft.
