# 935 blade cut coverage screen

A closed contour does not imply that it covers every segment in the observed
cut. For the quarantined blade-05 tip experiment, the selected contour omitted
37 of 559, 46 of 411 and 55 of 253 segments at stations 134, 135 and 136,
respectively. Values are in uncalibrated source coordinates. These omitted arcs
have not been identified; their exclusion is not justified by the presence of
a closed contour. The experiment and its nine-blade loft remain quarantined,
and the CFD admissibility record is unchanged.

The independent [coverage screen](../../../twins/935-horizontal-cooling-system-f0/source/audit_cut_coverage.py)
compares unoriented observed segment edges and selected contour edges after the
same six-decimal endpoint rounding used by the historical contour routine. It
counts multiplicity, separately reports added contour edges, and returns a
nonzero status if any observed edge is missing or any closure edge is added.
It tests coverage of the input segment set; it does not establish whether the
segments belong to the same physical blade, whether the cut is correct, or
whether an output surface is valid. Precision and duplicate geometry can affect
the count. Inputs and outputs must be kept private.

The prior reconstruction scripts remain byte-for-byte unchanged because they
are pinned by historical evidence receipts. This independent screen is not
integrated into those scripts: run it explicitly before accepting a future
contour. Prepare a private NPZ with `segments` of shape `(N, 2, 3)` and the
pre-fit selected `contour` of shape `(M, 3)`, then run:

```sh
python twins/935-horizontal-cooling-system-f0/source/audit_cut_coverage.py PRIVATE_INPUT.npz work/NEW_PRIVATE_REPORT.json
```

A passing result only means the selected contour covers all supplied edges
without adding edges at the declared rounding precision. It is not permission
to use the result as a physical datum or for manufacture.

The [private correction package](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-blade05-provenance-correction-20261104.tar.gz)
contains the visual overlay and sampled distances; its SHA-256 is
`a80f6e51ebdaf1d1d749719b1319a85343d0d38cc49571fdc65b93e1b264ccd3`.
