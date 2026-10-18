# Atomic candidate: actual polygon-distance evidence

Two fresh directed CUB queries passed the unchanged **0.0625 mm** polygon
representation gate, with maximum upper bound **0.0328639663163803 mm**.

| Direction | Query faces | Complete target faces | Lower (mm) | Upper (mm) | Gap (mm) |
|---|---:|---:|---:|---:|---:|
| Original patch to atomic candidate | 4,704 | 1,803,870 | 0.03193591661872411 | 0.031970337358431314 | 0.000034420739707205494 |
| Atomic patch to original | 3,868 | 1,804,706 | 0.03282758690510516 | 0.0328639663163803 | 0.000036379411275135054 |

Each interval is finite, ordered, nonnegative and has gap below the frozen
0.0001 mm limit. `results/interval-assessment.json` is the exact unchanged
assessor output. Original and candidate source lengths differ, so each direction
uses its own mask and the complete opposite target. This is continuous triangle
surface distance, with normalization disabled and the retained allocation rule;
it is not a vertex sample or a symmetric fragment-to-fragment comparison.

The source reduction removes an identical oriented exterior of 1,800,002 faces,
present exactly once in each complete surface. If A=S union A_patch and
B=S union B_patch, every point of S has zero distance to the opposite complete
target. Therefore h(A,B)=max(0,h(A_patch,B)), and likewise in reverse. Some patch
faces may also coincide; leaving them in the source is conservative. The exact
proof, preparation source, root import-binding record and complete-array peer
partition review are retained under `references/` and `reviews/`.

The candidate is identified by BIN SHA-256
`1f9dbd4cda61c7b58084479ebb165fb01280fa831752dc0da18517e548131b1a`;
the original by `894ece6e63d99684fd7c8710caf73132cd73731ac8bc667548c21c85962d4c95`.
The surfaces, origin array and distinct NPZ masks are excluded from this capsule.
Their hashes remain bound in its complete role-key input inventory.

Controller times were 4.756560584064573 s and 4.403033250011504 s. Maximum sampled
worker RSS was 1,008,926,720 and 1,059,831,808 bytes, from 41 and 38 samples.
Both processes returned 0, were reaped and were no longer running, with no
watchdog stop, monitor error or cleanup error. Declared controls were a 4 GiB
sampled-RSS stop, 300 s process-group deadline and two-thread environment limits.
No hard address-space or OS CPU quota is claimed. The earlier RLIMIT_AS metadata
refusal is preserved with its explicit transcription provenance; it ran no CUB
query. The two actual native logs are nonempty numeric JSON and copied exactly.

This capsule permanently records **polygon-distance evidence only**. Local
candidate guards and topology/intersection results have separate capsules and
are not conferred here. It supplies no native CAD or rounding-error certificate,
complete OEM/interface/feature qualification, accepted volume mesh, head thermal
or strength result, material/LPBF qualification, Omniverse solver field,
PhysicsNeMo dataset qualification or manufacturing authorization. The five-stage
engineering programme remains open.

The original execution summary says assessment pending and leaves its distance
flag false; it is copied unchanged. The separately produced exact interval
assessment and root/peer reviews record the later distance-only pass. Neither
review replayed CUB. The eight earlier numerical fixture outcomes remain bound
by their exact assessment; they were not rerun for this candidate. Matching
published source and runtime binary hashes is not a binary rebuild attestation.

`original-records.json` covers all 52 native inputs, two query configs and 13
original artifacts. `projections.json` explicitly selects safe child/lifecycle
fields. This is an assembled whitelist projection with selected exact originals,
not the full native records or standalone reproduction. Runtime binaries,
private machine paths and raw commands are excluded. See `ATTRIBUTION.md`.

Run `python3 verify.py` here for stdlib-only sealed closure, byte-count and
SHA-256 checks. This verifies capsule integrity only; it does not import a
scientific runtime, reopen a mesh, replay CUB or establish engineering approval.
The receipt excludes itself from the payload manifest.
