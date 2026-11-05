# Mandatory complete receipt

The final launcher uses `audit_complete_supports.py`. The six initial files
remain frozen; this wrapper adds proof that no entire material group
disappears between slicing planes.

```sh
work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python \
  parts/993-eng-carrier-0001/source/process-scanpath-audit-20261016/audit_complete_supports.py \
  PROCESS_OUTPUT PROCESS_OUTPUT/support-scanpath-audit \
  --source-stl work/part-workflow/run-001/surface/carrier-remeshed.stl \
  --part-cache work/carrier-process-20261016/part-layer-cache-001
```

The wrapper always runs the initial complete audit in `scanpaths/`.
It then searches, for each face group, for at least one real recorded
exposure equal to the correctly rounded encoding of its rational section.
The witness contains the group identifier, the source face, the layer, Z and the
vector. A sheet lying entirely between two planes is refused.

This second search uses layer witnesses after the mandatory check of
**all** layers. It cannot replace that complete audit. Its read cache is
bounded to eight layers and recomputes no part hatching.

The final receipt `assessment.json` binds by SHA the same `process/report.json`,
`scanpaths/assessment.json` and `group-exposure-coverage.json`. Both sub-receipts
must be accepted. The five initial flags are kept and
`every_material_group_exposed=true` is mandatory. The coverage sub-receipt
also carries `layers_audited`, `complete_build_audited` and the process SHA;
the provenance of the complete pass is recorded there.

Targeted check: `python test_complete_supports.py` (three witnesses,
including the sheet lying between two planes). The complete run on the carrier
still awaits the final process with its corrected supports.
