# Exact inclusion of continuous domains

`exact_polygon_coverage.prove_polygon_covered(source_polygon, target_polygon)`
returns a `passed` or `refused` receipt, with WKB digests and rational witnesses.
Both inputs must be valid, non-empty `Polygon`s, checked by
GEOS. `MultiPolygon`s are explicitly refused: the builder calls
this check separately for each connected free interval.

The proof uses no overlay and no proximity threshold. Each source edge
is split at all rational intersections with the target; its vertices
and each whole interval are checked. Once the whole source boundary is
covered, a component of the target's complement cannot cross that
boundary. One interior rational point of each target hole is then enough to
detect a hole entirely contained in the source material. The exterior
complement, connected to infinity, cannot be contained in a bounded source.
The `exact_contacts.py` kernel is loaded by path with its frozen SHA.

The [real chart35 witness](polygon-coverage-evidence/chart35-assessment.json)
keeps the refusal of the initial GEOS union: it creates a hole of positive exact
area, about `7.494598039e-18 mm²`. The hull of the offset triangles is not
at fault: for a positive penetration, the two IEEE roundings `z-p` and `z+p`
always bracket `z`.

On this single witness, the construction
`D.union(union_all(sweeps).intersection(allowed))` passes both inclusions
`D ⊆ result ⊆ allowed`. These local receipts do not constitute an admission of the
complete carrier. The builder must reproduce both proofs for each
real interval and keep their geometry links until sealing.

Targeted verification:

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest tests.test_carrier_exact_polygon_coverage -v
```

The ten tests cover in particular an edge that crosses a notch despite its
covered vertices, a hole one ULP wide, holes in the source, the refusal
of `MultiPolygon` islands and the full reproduction of the four real receipts.
