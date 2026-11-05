# Mission: reconstruct the 935 cylinder head from the raw data

You are steering non-commercial R&D. No 993 model or earlier cylinder head
result may be used as input. Do not infer millimetres from expected
dimensions. The scan does not prove hidden galleries, materials or loads.

Read `results/intake/intake.json` and the CAD-Recode proposals placed by the
operator in this workspace. Produce a CadQuery script `candidate-1.py`
holding the result in `r`. The coordinates of this script are CAD-Recode's:
normalised point cloud multiplied by 100; the worker cancels this factor.

To request an execution, write `requests/export-1.json`:
`{"stage":"export","attempt":1}`. The external dispatcher executes only
this contract. Read `results/export-1/execution.json`, then request the
evaluation with `requests/evaluate-1.json`: `{"stage":"evaluate","attempt":1}`.
Read the report `results/evaluate-1/report/deviation.json`.

Three proposals at most (1, 2, 3). Do not replace a proposal that has already
been executed. Fix syntax from the errors; do not claim to improve a geometry
you have not measured. Do not rewrite any result, threshold, digest or source
data. Stop after three failures and explain the persistent defects.

A valid STEP is only a candidate reconstruction. Deviations remain in OBJ
units. Any dimensional promotion, physical property, manufacturing or 993
compatibility requires evidence and human review. No purchases, no paid API,
no access to secrets or to earlier geometries.
