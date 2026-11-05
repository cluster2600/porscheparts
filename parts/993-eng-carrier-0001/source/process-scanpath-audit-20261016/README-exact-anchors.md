# Exposure contacts decided before encoding

The new entry point of the complete audit is:

```sh
AM_PYTHON parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports_exact_anchors.py PROCESS OUTPUT --source-stl STL --part-cache CACHE
```

It keeps the complete vector checks, their independent sections, the two
contact domains, the successive graphs and the exposure of at least one
section of each material group. The old auditors remain unchanged and are
loaded in isolation with a check of their digests.

The anchoring decision uses the rational intersection between the contact and
the raw part rings of the same plane. It does not round the contact before
this test. Ring parity defines the material; the coordinates of a GEOS overlay
do not serve as the measurement domain. The floating-point length published in
the witness is a diagnostic computed after the exact decision. A point-only
contact does not constitute a positive anchor.

The connectivity of the IEEE vectors is checked separately after their
correctly rounded encoding. Its anchors come from the certified rational
contacts; no beam width or proximity distance is added.

The [negative witness](exact-anchor-evidence/negative-ieee-hole.json)
reproduces the earlier error: an exact contact meets the material only at its
end points, but rounding it before intersection gives GEOS a positive length
of about `0,81397 mm`. The witness's contact trace is itself obtained by exact
clipping and its encoding is verified, rather than injected as inconsistent
private data. The new adapter refuses this anchor. This software witness does
not claim to describe the future real preparation.

The summary `assessment.json` and `scanpaths/assessment.json` both carry
`rational_part_contact_intersections=true` and
`part_contact_intermediate_encoding=false`. The receipt
`group-exposure-coverage.json` keeps its previous contract. All are bound to
the same SHA of `PROCESS/report.json`; no new part geometry receipt is needed,
since its layer NPZ files and the complete cache are already verified.

```sh
AM_PYTHON -B -m unittest tests.test_carrier_exact_exposure_anchors -v
```

Ten targeted tests cover the defect before the fix, its refusal after the fix,
the real contacts, the plate at the first layer, holes, non-dyadic rational
parameters, the sheet between planes and the two new fields.
Delivering this code does not constitute running the real complete audit.
