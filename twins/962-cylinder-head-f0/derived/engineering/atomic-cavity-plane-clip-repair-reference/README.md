# Clipped surface: read-only repair reference

The completed reference describes immutable clipped candidate
`d2af68ee8ab242e992b15b6e2a93ac7e487972277af7f31a8496a7036ec32240`.
It records masks, the complete exact-z=0 cap and shortest-edge observations.
**No keeper, target policy, repair constraint or geometry change was selected.**
The 3,112 triangles below 2/29 still reject the surface.

| Recorded observation | Result |
| --- | ---: |
| Exterior-only fixed vertices / legacy fixed vertices | 865,429 / 865,429, equal mask bits and hash |
| Incident-region vertices / boundary vertices | 5,938 / 2,012 |
| Vertices not exterior-fixed | 3,926, exactly patch minus boundary |
| Complete all-z=0 cap vertices / edges / faces | 3,508 / 7,016 / 3,508 |
| Abstract cap Euler / edge components / boundary cycles | 0 / 1 / 2 |
| Abstract cap cycle lengths | 1,482 / 2,026 |
| Cap faces inside / outside the incident region | 3,470 / 38 |
| Poor cap faces | 2,396 |
| Poor triangles with tied shortest-edge minima | 4 |
| All-tied / exploratory lexicographic-first edge counts | 2,700 / 2,696 |
| Union-find groups in each full-poor-face scenario | 476 |

The complete cap is an abstract oriented annulus with exact rational negative-Z
winding on every listed triangle. Its cycles do not establish physical holes,
void coverage, cooling-passage identity or permission to alter the cap. The
cap and incident-region boundaries are separate records. The observed masks
are not approved repair constraints.

All three squared edge lengths of each frozen poor triangle were ordered using
exact rational representations of its stored binary64 coordinates; every
minimum tie is retained. The two graph scenarios have the same group membership
in this result. Neither chooses an edge policy. Necessary-only keeper lists use
the conditional exterior-fixed rule and exact-z=0 restriction for cap members.
Zero recorded fixed-conflict groups does not establish quotient, link, normal,
quality, neighbor, envelope or keeper admissibility. No keeper was chosen.

The [full report](readback-report.json.gz) is losslessly compressed from
8,223,588 bytes to 550,611 bytes. Its original JSON SHA-256 is
`ebf9dd540d32ff6dd2d47267a94d8500b498b30e783288a91eba5c556d21b108`.
The [format receipt](report-format.json) records the compressed identity,
deterministic level-6 gzip with an empty filename and zero modification time,
complete decompressed-byte equality and CRC verification. The full report is
preserved without duplicating its uncompressed JSON here.

The optional [mixed-poor query](exploratory/mixed-poor-query.json.gz) is explicitly
**exploratory**. It restricts saved records to 716 mixed poor faces with no ties:
both scenarios contain 716 edges and 506 groups on 1,222 vertices, all on the
first abstract cap cycle in the report's retained order. This selects no keeper,
geometry or repair policy. Its original JSON SHA-256 is
`ceb6769c7ab98cd666a1d73fefa8e56e999440abd0d6a7ba41eeb675d6cbaff5`;
the [query format receipt](exploratory/query-format.json) binds all 222,679
original bytes to the 5,299-byte gzip with complete lossless readback.

The exact [root result review](reviews/root-result.json) independently checks
the complete masks and cap membership with a full saved-face scan. Its
shortest-edge arithmetic review was delegated. The exact [independent result
review](reviews/result-peer.json) checks every poor triangle's rational lengths
and ties, all listed cap windings, reported rim rows, group memberships and
necessary-only lists using bounded original BIN rows. Its stated limits retain
the original reader's full-scan attribution where it did not independently
repeat completeness checks. Neither review replays a scientific/native audit.

The [execution receipt](execution-receipt.json) records return code 0, no stop,
1.332 seconds of controller wall time and three RSS samples reaching
294,338,560 bytes. The unchanged controller used a 120-second wall deadline,
sampled 4 GiB worker-RSS stop and two library threads. These are not hard OS
memory/CPU quotas or a certified peak. No independent OS PID-absence probe is
claimed. The [log](native.log) and report record completion. The reader's
0.897-second observation includes no repair, mesh export or solver call.

The executed [reader](source/reader.py), [reference helper](source/reference_kernels.py),
[patch kernel](source/patch_kernels.py), [controller](source/run_readback.py) and
[kernel test source](source/test_reference_kernels.py),
[five-method result](tests/kernel-tests.json), [test log](tests/kernel-tests.log),
[source provenance](details/source-provenance.json), [preparation checks](details/preparation-checks.json),
[root source review](reviews/root-source.json) and [source peer review](reviews/source-peer.json)
are exact copies. [METHOD.md](METHOD.md) preserves its earlier held/unrun stage.
The subsequent execution and reviews provide the completed observations.

[Original records](original-records.json) retain all eight original output
identities, the complete 32 launch pins, and every selected copy, compression
and projection association. The [launch contract projection](native-contract-projection.json)
and [held preparation projection](details/preparation-contract-projection.json)
omit only their private absolute `native_python` path. All other values and
pins remain exact, including the historical `native_launch_authorized: false`
and actual `readback_launch_authorized: true` fields in the launch contract.
This selected companion contains no large candidate or runtime. Source/test
replay requires its original bound inputs, runtime and repository layout.

The preceding whole-surface global reference remains a separate recorded
baseline. This reader establishes no semantic cap/void or interface mapping,
new quality acceptance, continuous-distance result, admissible quotient,
approved surface/volume mesh, head physics, material, LPBF process or
manufacturing qualification.

After sealing, `python3 -B verify.py` checks only payload hashes, sizes and file
closure with the reused standard-library verifier. It does not decompress the
JSON, import the reader, repeat any query or grant engineering acceptance.
