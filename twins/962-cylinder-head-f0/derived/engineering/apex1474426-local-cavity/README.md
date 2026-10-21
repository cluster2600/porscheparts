# Apex 1474426: original star, local meshes and parent context

The original 60-cell star was extracted and independently checked. One
fixed-shell generation failed the unchanged SICN 0.1 gate. A subsequent single
saved-cavity Netgen operation passed the local native quality and saved-identity
checks. The separate read-only parent-context census completed. No head edit,
embedding, same-domain or physical acceptance follows from these results.

| Stage | Observed result |
| --- | --- |
| Original-star extraction | 60 original cells, 33 source nodes, 32 shell nodes, 60 faces, 90 edges, Euler characteristic 2. All 60 tight necessary face bounds are strictly above 4/841. |
| One local generation | 32 nodes, 57 TET4, no interior nodes, 11 positive poor cells; minimum native SICN 0.009188807754622056. Natural return code 2. |
| Current parent context | 38 exterior faces and 22 internal interfaces, 20 distinct outside tetrahedra and 32 outside nodes. Natural return code 0. |
| One saved-cavity Netgen operation | 40 nodes, 101 TET4, eight interior nodes, no poor or nonpositive cells; minimum native SICN 0.13807503254019585. Natural return code 0. |

The extraction retains every original ordered cell, tag, coordinate word,
local/global map, exact volume and face certificate. Its 32 shell nodes comprise
27 original source-boundary nodes and five original dim3 nodes; the apex is
excluded. The face screen is necessary only and does not prove meshing
feasibility. Generation and Netgen temporarily fix all 32 shell nodes. The
original head classifications are retained separately.

The first generated mesh remains preserved with all 11 failed quality rows.
The Netgen operation starts from that exact saved state. A volume-only geometry
flag must leave its complete state unchanged before the single forced Netgen
call and cache refresh. Every after-state cell receives native metrics and
signed-volume/incidence audits. All 32 shell coordinate words and 60 oriented
triangles remain fixed. Full before, geometry-flag, after and saved arrays are
retained; after and saved states match exactly. The eight new local interior
tags are 33 through 40. They have no inferred ancestry or head storage policy.

Independent saved-row reviews reconstruct the local determinant, volume and
quality observations. Native reopening is attributed to the workers. The tiny
MSH bodies retain exact byte identities; their independent review has only the
decoding scope explicitly recorded by each stopped peer. Positive cells,
opposite internal faces and matching volume do not establish geometric
embedding, absence of overlaps, containment or domain equality.

The context retains all 60 face-owner, corner and orientation associations,
selected coordinates, classifications, entity/parameter rows, outside rows,
global tag maxima and preservation hashes. Among the 33 original selected
nodes it observes 27 dim2 and six dim3 nodes, including the apex. The independent
peer checks the saved associations. Complete global enumeration and fresh
native observations remain attributed to the reviewed reader and root; the
saved subset alone cannot exclude omitted owners. Local quality does not
authorize replacing any of those parent cells.

## Selected evidence

Each stage includes editable source, focused guards, complete results, held and
actual authority records, root closure and source/child/result reviews:
[extraction](extraction/results/saved-star-observation.json),
[generation](generation/results/fixture-report.json),
[context](context/results/readback-report.json), and
[Netgen](netgen/results/fixture-report.json).
The local JSON and tiny MSH files intentionally export geometric analysis data.
[original-records.json](original-records.json) records every original four-,
eight-, six- and eight-file inventory, input/runtime hash map, snapshot
association and projection. Numerical values, coordinate hex, tags, timings,
RSS samples and statuses are preserved. Sampled RSS is not a true peak or hard
quota. Historical held flags stay historical; actual records separately granted
only the completed bounded operation.

Private host paths become explicit project-relative or runtime roles. Only
explicit PID, PPID and PGID values become consistent process roles. An observed
truncated process-comm label is explicitly projected as a truncated label,
without inferring its executable identity. Logs and affected fields remain
complete. The context selfcheck is a plaintext source projection because its
registered NumPy-origin literal contains a private path. Every original size
and SHA256 is retained; projections are not labelled exact copies.

Unchanged bodies are linked rather than duplicated: the
[current full-star census](../head-star-remaining-full-stars/results/readback-report.json),
[partial-head proof](../head-star-replacement/results/readback-report.json),
[rejected coordinate trial](../head-star-remaining-sicn-proposer-rejected/README.md),
[prior generation](../fixed-shell-generation-apex1435493/README.md),
[prior saved-Netgen source and controller](../fixed-shell-netgen-apex1435493/README.md),
and [fixed-face source](../../../source/certify_fixed_face.py).
The ledger binds 17 exact existing public dependency bodies. These were checked
in the local publisher checkout, not remotely re-attested by this selection.

This is selected evidence with original work-layout paths and selected runtime
identities, not an independently runnable distribution from these source
folders. The full private parent mesh and runtime binaries are omitted. No
complete private-input, package, ABI or operating-system closure is claimed.
There was no optimizer, solver or mesh write in the context query. The parent
still has 208 positive poor cells under the unchanged gate. The stronger 414
criterion and PDE, material, strength, LPBF, OEM, manufacturing and physical
qualification remain open. There is no head application, stitch or approved
replacement in this capsule.

Run `python3 verify.py` to check the selected byte seal. It checks bytes only,
without scientific replay. Reuse follows the included
[project licence](LICENSE.project).
