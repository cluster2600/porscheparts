# Actual scalar plot and retained reproduction inputs

The actual render returned RC0 under the unchanged retained owned supervisor (4d18):
180 seconds outside, a 150-second renderer alarm, CPU 140/141, child nice 10
once, BLAS 1 and zero workers. The child used the original Python 3.10 executable
with -B and NO-I, preserving its existing user-site plot runtime. All 219 runtime
files and all 240 launch pins remained unchanged. No CAD, mesher or solver ran.

The complete original argv, plan, three pending/armed control pairs, logs,
read-only collector and closure are retained under proofs/render/. The original
renderer is source/figure.py. Its five pure helpers remain literal copies from
the earlier plot source. The 18 small non-runtime inputs have explicit original
workspace aliases in workspace-aliases.json; the external 219-file runtime and
the raw 07b354 BREP are declared separately. The BREP was only byte-hashed by the
original preflight and is not copied or imported by this figure.

The captured exact law contract and original Fraction restriction source are
under source-inputs/, with their original workspace paths. They prove every
actual knot span, without a sampling test, epsilon or radius grid. The complete
retained proof is also present in data/law-data.json and the native/render
receipts. No stock post-Build curve or Solid is supplied.

The stored source and original commands allow inspection of the actual run;
they are not a new execution authorization or an executed portable plot replay.
Reconstituting a fresh workspace requires the declared aliases, original
relative helper hierarchy, exact external runtime and raw dependency, a newly
reviewed plan and a separate ROOT GO. No restoration or rendering runs during
this capsule's publication. The PNG was independently viewed; the PDF was
checked for its header and embedded font but was not raster-reviewed.
