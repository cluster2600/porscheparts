# Two isolated apex optima: rejected simultaneous proposal

One deterministic standard-library query moved only cavity nodes 28 and 29 to
the centroid-normal optimum for their respective fixed faces. On the complete
39-cell cavity, it was rejected: positive cells **181, 203, 205 and 207** are
below SICN 0.1, and cells **211, 214 and 215** are strictly inverted.
The original two target cells improve, but their isolated optima harm other
cells. This result establishes neither repair feasibility nor impossibility.

The [full diagnostic](results/diagnostic.json) retains all 19 proposed coordinate
rows with binary64 hexadecimal values, both constructions and all 39 ordered
cell results. Determinants and squared SICN values are exact Fraction evaluations
of the proposed binary64 coordinates; signed decimal qualities are approximate,
with no interval or native-quality claim. All 16 shell nodes and node 27 remain
bit-identical, and connectivity is unchanged. Matching signed volume and
oriented face incidence do not establish embedding, containment or non-overlap.

The [method](sources/METHOD.md), [editable caller](sources/propose.py) and
[self-check](sources/selfcheck.py) are preserved unchanged. Root ran the compact
self-check once, then one query under an ordinary 10-second subprocess timeout.
The query returned RC2 naturally in 0.124909 seconds, without a timeout or retry;
its stdout and stderr are empty. This control is not a hard OS CPU/RSS quota.
The [independent stopped-result review](reviews/result-peer.json) reconstructed
both rounded target constructions and all 39 exact determinant/quality rows:
32 pass, four positive cells are poor, and three are inverted. This is an
analytic saved-coordinate check, with no native quality replay.

The input is the complete saved 19-node / 39-cell
[Netgen cavity](../fixed-shell-netgen-apex1435493/README.md), bound by arrays
`ace411a27a13332129f515ac456ab453cbede0920fe115bdb82057092e665e5f`
and worker `8529a8f8421dd989ae243b2a06b132b8a2952e9847aa31d34adb74289a16e6c7`.
The [local shell](../direct-sicn-apex1435493-cavity-study/study/local-shell-input-001.json)
and [fixed-face proof](../../../FIXED_FACE_QUALITY.md) remain linked references.
[Original records](original-records.json) bind their exact hashes and explain
the two explicit runtime-path projections. Earlier unrun/held status fields
remain historical; completed source, child and execution records are separate.

This is selected evidence with retained original work-layout paths and a
selected Python interpreter, not an independently runnable distribution from
`derived/sources/`. The byte verifier checks selected bytes and closure only;
it does not replay the geometry computation. No native mesh application, MSH
write, head stitch or physical qualification occurred. All engineering,
physics and manufacturing acceptance flags remain false. The current
[project licence](LICENSE.project) applies.
