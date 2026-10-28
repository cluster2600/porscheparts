# Held single two-apex analytic proposal

Source preparation only. The current Netgen cavity is bound by complete saved
arrays `ace411a2…`, worker `8529a8f8…` and stopped peer `737cafa9…`: 19 nodes,
39 cells, only native cells 198 `[29,4,5,6]` and 204 `[28,7,9,8]` below SICN
0.1. The caller proposes a new position once for each of nodes 29 and 28 using
its respective fixed face. Node 27 and all 16 shell nodes remain bit-identical.
No source function, self-check, scientific import or query was executed here.

The retained fixed-face proof supplies the ideal-reference expression. For
face edges e1/e2, use a=e1, b=(2e2−e1)/√3, A=|a|²+|b|² and
T=|a×b|²=4|e1×e2|²/3. A centroid-normal apex has c=z·n, where
z=√(3/2)h. Its squared SICN is

`9 T z² / ((A+z²)(T+A z²))`.

Writing x=z², the derivative has the sign of T−x². Thus the real isolated
maximum is at z²=√T, physical height h=√(2/3)·T^(1/4). This also recovers the
retained ceiling 3q₂/(2+q₂). The old side and native-order determinant are
computed exactly with Fraction; a negative or degenerate original target is
refused. Centroid/normal construction is rounded once through ordinary Python
binary64 arithmetic. There is no claim that its rounded point is the exact real
optimum or a global optimum for all incident cells.

The certificate's `rational`/`certificate` and exact-pair `subtract`/`dot`/`cross`
functions are copied unchanged. The new complete metric uses rational columns
a=e1, b=2e2−e1, c=3e3−e1−e2, with

`N=|a|²+|b|²/3+|c|²/6`,

`K=|b×c|²/18+|c×a|²/6+|a×b|²/3`,

`Q²=18 det(e1,e2,e3)²/(N K)`.

That is the same ideal-reference inverse-Frobenius SICN normalization without
irrational arithmetic in its squared evaluation. The actual proposed binary64
coordinates are converted exactly by Fraction. Every one of the 39 unchanged
ordered cells must have positive determinant and Q²≥1/100; decimals are
informative signed square roots, not native or interval measurements. Undefined
or nonpositive cells fail. There is no threshold relaxation or epigraph proxy.

The query retains all 19 proposed coordinate rows with hexadecimal binary64
values, both target constructions and all 39 signed-quality records. It checks
unchanged connectivity's complete oriented face incidence and exact before/after
signed-volume sums against the original cavity fraction. A rejected candidate
is retained in `diagnostic.json` with RC2; an analytic local pass returns RC0 but
still authorizes no native coordinate application. No MSH is written.

The single compact stdlib assert check covers exact unit-axis Q²=2/3, regular
face apices at native corners 3 and 0, the anisotropic-face cap, old-side sign,
changed-tag refusal, signed-zero preservation and missing/changed before pins.
It is prepared and unrun. Root must review/run it, freeze a separately reviewed
actual contract and interpreter/resource/watchdog observations, then authorize
one stdlib query into a fresh output. Output and actual-child identity remain
null in the held contract; no new controller is supplied.

The two isolated optima may harm other or shared cells. The full 39-cell gate
evaluates the simultaneous proposal; success or rejection is unknown. Matching
volume and integer incidence do not establish geometric containment,
non-overlap, embedding or head stitchability. All native/head/stitch/physical
authorities stay false. There is no solver, iteration, grid, fallback or retry.
