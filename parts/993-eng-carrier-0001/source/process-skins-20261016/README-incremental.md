# Exact incremental construction of the sheets

The entry points `generate_prism_region_v5.py` and
`generate_legacy_region_v5.py` keep the arguments, checks and
outputs of v4. Their private module `continuous_incremental_interfaces.py` keeps
the cf269 repair policy and uses builder 814. The old
builders, rejected work and frozen sources remain present.

The incremental update recomputes only the lines touched by the two
triangles of a new quadrilateral. It keeps the endpoints of cancelled
edges, the oriented events and the order in which lines appear. A rejected
trial does not modify the accepted state. Coordinates remain exact
fractions of the recorded IEEE values. Point identifiers speed up
only equality and ordering: an IEEE key is accepted only after
proof that its rational representation is identical. No coordinate computation
uses these keys. The lock and the re-entrancy guard protect the private
substitutions; the public module remains intact.

The five small captures reproduce exactly the WKB of the result and receipt
943. The tests also cover cancelled endpoints, a rejection followed by an
acceptance, IEEE neighbours, non-representable coordinates, re-entrancy
and a flat snapshot loaded from `/`. The full pass over large skin 1
contains 5,876 vertices, 5,875 calls and 5,874 accepted additions, with no fallback to
full recomputation: 324.729 s measured. This time is not a speed ratio
against an earlier full pass, which did not finish. A single reconstruction
by the original 943 function of the 17,622 finally accepted triangles gives the
same WKB and exactly the same rational area.

These proofs concern the builder. The seven regions must still
produce their checkpoints; sealing the six admissions, slicing the
supports at the 1,034 real planes and the full audit of exposures remain
separate steps. The part cache and the admitted native envelopes are
reused without recomputation. The compact receipt is
`combinatorial-evidence/incremental-results.json`; the detailed local results
are linked to it by SHA.
