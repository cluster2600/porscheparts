# Relocate3D: a completed, rejected trial

One bounded relocation of the saved Netgen volume increased positive
**SICN < 0.1** cells from **210 to 226** and reduced minimum SICN from
**0.039074265058645995 to 0.038263551144442014**. The unchanged **SICN >= 0.1**
gate rejected the result naturally, with return code 2 and no watchdog stop.
The [prior Netgen result](../atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport/README.md)
remains the better rejected mesh; this output does not replace it.

The complete [worker report](reports/worker-report.json) records **1,097,048
nodes**, **3,620,809 tetrahedra**, 225,317 referenced interior nodes and zero
orphans. Native Jacobians, native volumes and independent signed volumes are
finite and positive. Summed signed volume is **915453.1236217882 mm³**, with
relative error **1.1102230246251565e-16** against the source volume reference.
The output MSH is 235,742,414 bytes, SHA256
**7bc4a1641e4131a9caf926f83d70740270bfb8077ac6c2ecad24fde9d7721b36**;
its body remains private. No post-relocation boundary/interior poor-cell bins
were computed. The [earlier saved diagnosis](../atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-optimized-diagnosis/README.md)
classifies the input's 210 cells only; those bins are not transferred to 226.

## Operation and observations

The exact [executed wrapper](sources/mesh_relocate3d_postexport.py) is
SHA256 **056115fc9653ec19c54731617a8d5071da774ed10f2eea61739fee87b9352597**.
It is a byte-reversible successor of Netgen002, with complete unchanged audit
and owned-controller helpers. After a fresh full audit against the sole
Netgen worker.after baseline, it attempted `Relocate3D(niter=1)` once, without
force or createGeometry, then rebuilt the element cache once. These counters
record attempts, not independently observed backend sweep counts.

The [source note](sources/NOTE.md) and [primary bindings](sources/primary-source.json)
show that release-source niter=1 means **three vertex-star sweeps**, optimizing
signed Gamma rather than SICN. This is source-derived behavior, not runtime
sweep telemetry or attestation that the installed binary matches that archive.
The dimensionless line-search tolerance is not a dimensional repair/manufacturing
tolerance. The source permitted only interior-coordinate changes, with fixed
node/tetra tags, oriented connectivity, classifications and full boundary.

The worker repeated full incidence, opposite internal orientation and field
audits, saved the output, reopened it and recorded exact full tagged-array,
classification and saved-file identity. Its observations preserve the source
boundary, including the 38 fixed cap cells. These scientific predicates are
**worker observations**, not an independent MSH replay by this capsule or its
stopped-result reviewer. [The peer](reviews/result-peer.json) states that scope.
The negative result is about this one proposal, not general repair feasibility.

## Bounded lifecycle and a preserved observation error

Worker/native-window/outer times were **251.433572167 / 252.940262416 /
255.979783583 seconds**. The native log separately times the optimizer itself
at **42.3206 s wall / 41.1856 s CPU**; the larger windows include full audits.
There were 492 RSS samples, maximum **5,240,897,536 bytes**. The 1,200 s
native window, sampled 8 GiB RSS and sampled 1 GiB output
thresholds and two software threads are not hard OS RAM/CPU/disk quotas or
proof of an unsampled peak. All **141 input and three runtime hashes** remained
unchanged; the owned process was waited/reaped, and the root's later individual
controller/worker absence probes are retained with private PID values removed.

The prelaunch and [first live comm-filter observation](reports/live001-false-negative.json)
incorrectly returned empty matches because macOS truncated the executable column.
They are preserved as false negatives, not evidence of prelaunch absence.
The [corrected full-argv live observation](reports/live002-projection.json)
observed the owned controller/worker pair while running and no other selected
known-token process. This was contemporaneous evidence only: it does not
retroactively repair the prelaunch guard or establish universal exclusion of
all native processes. The terminal [root projection](reports/root-closed-projection.json)
keeps that limitation explicit.

## Selected evidence and limits

This selection contains exact source, tests, source/delta notes, worker report,
reviews and the full native log with **only its two absolute mesh locators
replaced by named input/output roles**. The log is a projection, not an exact
copy. JSON projections remove argv/PID values, raw RSS series and private
runtime locators while retaining original digests, complete 12-file inventory
and current before/after input maps. Six executed-source identities are bound;
the five unchanged dependency bodies are linked, byte/hash-checked, to existing
public capsules instead of duplicated. Historical held/pending/unrun metadata
are preserved; separate root six-test, child and terminal records establish
later events without rewriting those files.

[Original-records](original-records.json) specifies every copy, projection,
omission and dependency link. This is not the full private dependency/run
closure or a standalone reproduction. The unchanged stdlib
`python3 -B verify.py` verifies sealed bytes and closure only; it does not
import scientific modules, rerun optimization or certify numerical metrics.
Upstream source/runtime bodies and the large MSH are excluded.

All physical acceptance flags remain false. The 0.0625 mm analysis-surface
representation budget and 414 unmet stronger Mesh_2 conditions are unchanged.
There is no accepted/converged head volume, new solved head field, thermal or
strength prediction, OEM/feature upgrade, material/LPBF qualification,
engineering release or manufacturing authorization. Project-authored material
retains the [project licence](LICENSE.project); third-party rights remain separate.
