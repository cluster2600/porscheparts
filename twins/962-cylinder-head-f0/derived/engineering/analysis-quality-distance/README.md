# Continuous polygon-distance evidence

The two directed continuous distance queries passed the unchanged **0.25 mm**
envelope and **0.0001 mm** interval-gap limits. This capsule concerns the
generated bore95 study surface. “Original” does not mean a measured Porsche
component, and these results establish neither solver admission nor physical
qualification.

| Direction | Lower (mm) | Upper (mm) | Gap (mm) | Wall time (s) |
| --- | ---: | ---: | ---: | ---: |
| Original → candidate | 0.07185669700547284 | 0.07192052963427972 | 0.00006383262880688134 | 3.135 |
| Candidate → original | 0.07056987737974417 | 0.07062596035893927 | 0.00005608297919509897 | 3.415 |

The [head interval assessment](head-interval-assessment.json) and the two
[head reports](head-execution-controls.json) retain the exact scalar results.
Both workers exited successfully, were reaped, and preserved all 92 frozen
input bindings. Maximum sampled worker RSS was 1,062,223,872 bytes.

The [exact union proof and partition metadata](union-partition.json) identify
1,800,014 shared oriented coordinate triangles and 4,692 changed triangles
on each side, out of 1,804,706 triangles per surface. With
`A = S ∪ A_changed` and `B = S ∪ B_changed`, every point of `S` has zero
distance to the opposite full surface. Thus
`h(A,B) = max(0,h(A_changed,B))`, and likewise in reverse. Each query retains
the **complete opposite target**. The
[independent crosscheck](independent-reduction-crosscheck.json) verified every
face by direct equality under three cyclic permutations, without importing
the canonicaliser. Neither comparison uses coordinate rounding or sampling.
The facet mask and geometry arrays remain private and are identified by hash.

The [eight original numerical fixture results](fixture-assessment.json) use
the [predeclared analytic references](fixture-contract-projection.json).
Asymmetric containment gives full/reduced `A→B=0` and `B→A=1`; the shared
target case gives `0.125` both ways. Discarding that target would incorrectly
give `0.25`. These fixtures also exercise open source fragments.

[Monitor hardening](monitor-hardening.json) is separately attributed: the
original controller produced all eight fixtures, and the later controller
produced the two head queries. A focused mocked observer-timeout test verifies
owned-process-group kill and reap before returning a refusal. Numerical
fixtures were not repeated for this change.

The [head contract projection](head-contract-projection.json) records the
sampled 4 GiB RSS stop, 300-second process-group deadline, serial native CUB
and two-thread environment. These are **not hard address-space or OS CPU
quotas**. RSS sampling and scheduling have observation latency. The preceding
[RLIMIT_AS refusal](prior-RLIMIT_AS-refusal.json) occurred before any CUB query;
its note is explicitly a transcription, not an original stdout capture.

[Runtime and source provenance](runtime-source-provenance.json) pins Python
3.13.16, NumPy 2.2.6 and CUB 1.0.0, plus interpreter/module/binary/source
hashes. The matching PyPI source builds the target AABB and subdivides only
the source; its last argument is `normalize`, not symmetry. Matching source
version and runtime fixtures do not attest a rebuild of the installed binary.
The interval result has no rounding-error or native-CAD certificate.

[Original input bindings](original-input-bindings.json) preserve all 92 input
hashes with host paths replaced by artifact roles. The
[original final receipt](original-final-receipt.json) is a byte-identical safe
copy; its retained-artifact list also names private artifacts not published
here. Whitelisted projections are explicitly distinguished from byte-identical
reports. Local receipts are not signed hardware execution attestations.

The [capsule receipt](receipt.json) binds only immutable payloads in this
folder. The external [working distance note](../../../source/QUALITY_DISTANCE.md)
remains navigational and is excluded from that manifest. This capsule contains
no access commands, host tool paths, executables, geometry arrays or new native
run. Complete Porsche interfaces, channel/BCC semantics, tetrahedral quality,
whole-head mechanics/LPBF and manufacturing approval remain separate gates.
