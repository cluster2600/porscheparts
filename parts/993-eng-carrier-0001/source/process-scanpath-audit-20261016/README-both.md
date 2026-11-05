# Contacts in the free domain and in the material

This extension keeps the frozen historical auditors and predicates. It
handles a projected source interface part of which leaves the unfolded free
domain: the contact kept is exactly
`interface_source ∩ domaine_libre ∩ matière_générée` (source interface ∩ free domain ∩ generated material).

`exact_contacts_both.py` combines the rational intersection parameters with
the contours of **both** polygons before checking each interval. The
holes are kept. The coordinates are encoded only once, after the
exact clipping; no buffer or geometric threshold is introduced. A
non-zero exact interval that collapses in float64 remains refused.

The API is:

```python
clip_contacts_in_both(material, domain, interfaces_raw)  # segments Fraction
round_contacts_in_both(material, domain, interfaces_raw)  # encodage final
contact_encoding_check_in_both(material, domain, interfaces_raw, recorded)
```

Each contact and each face group carries the same
`free_domain_geometry_wkb_hex`, `free_domain_geometry_sha256` and
`contact_clip_scope`. The latter equals
`source_interface_intersect_material_intersect_free_domain_exact_before_single_float64_encoding`.
The source interfaces remain raw; the contact traces contain
only the final encoding of the intersection in both domains.

## Complete audit

```sh
"$AM_PYTHON" parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports_both.py \
  PROCESS OUTPUT --source-stl SOURCE_STL --part-cache PART_CACHE
```

`audit_support_scanpaths_both.py` validates the WKBs and their SHA at the contact and
group level. It loads an isolated instance of the historical complete auditor whose
SHA it verifies, then replaces only its two contact predicates.
The same material/interfaces pair associated with two distinct domains is
refused, independently of the group order. The complete layer loop,
the independent triangle cuts, the chronological graphs and the
check of real contact with the part/plate are kept.

The complete wrapper still requires real exposure of **every** group.
The receipt contract remains `assessment.json`, `scanpaths/assessment.json` and
`group-exposure-coverage.json`, with their digests and the same SHA of the
process report. The main receipt also requires
`every_material_group_exposed=true`.

## Checks kept

The [compact results](both-contact-results.json) link the sources, fourteen
targeted tests and the [real chart225 case](both-contact-evidence/chart225-assessment.json).
Its [inputs](both-contact-evidence/chart225-inputs.json) are kept with
their original coordinates. The computation certifies five upper segments and two
lower ones in both domains; the errors of the final encoding alone remain
less than or equal to half an ULP.

The negatives cover a bridge over a hole, a one-ULP alteration,
an inconsistent WKB identity, a missing scope field, an ambiguous domain and
a material group located between the exposure planes. This witness does not constitute
a complete audit of the carrier supports: that awaits the complete
corrected process.
