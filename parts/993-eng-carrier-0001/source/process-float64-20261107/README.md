# Current carrier float64 layer replay

This entrypoint replays **only layer 517** of the admitted current carrier exterior
using the previously recorded macOS arm64 / CPython 3.11.18 runtime. The existing
v3 workflow executed both its preparation controls and the actual current-source
stage on 7 November 2026. All reference arrays and the complete native NPZ were
byte-identical; unchanged native and independent domain audits passed. See
[the compact execution receipt](validation.json). The bounded worker completed
in 19.04 seconds with a sampled peak group RSS of 4.13 GB and confirmed cleanup.

The private mesh is read directly as a little-endian `<QQ` count header, followed
by `<f8[nv,3]` coordinates and `<u8[nf,3]` ordered faces. Its exact bytes, coordinate
arrays, pose, native process parameters and reference layer arrays are pinned.
No STL import or conversion is involved.

## Reused sources

The existing `scripts/run_part_workflow_v3.py` remains the recipe runner.
`layers.py`, `build_pyslm.py`, `audit_scanpaths.py` and `part_cache.write_layer`
are loaded from their existing repository paths. The old STL full-cache builder
is never called. `parallel_layers.py` is retained as a pinned future migration
dependency; this direct single-layer command does not create its worker pool.

`strict_plane_oracle.py` contains the three pure function definitions copied
verbatim from the qualified strict source-edge oracle. Their source and AST
hashes are recorded. The historical standalone harness and its host paths are
not copied. `outward_bounds.py` and `owned_process_group.py` are byte-identical
copies of their qualified sources.

## Explicit private inputs

Copy `private-input.example.json` into the ignored location
`work/carrier-float64-layer-input.json` and supply all six local paths. The
manifest must identify the current source and layer 517. The mesh, admission,
recorded runtime profile, reference receipt and reference arrays must match
the hashes in `source-manifest.json`. The runtime profile includes 2,454 source
and native-file identities, and its package root must match the supplied path.
The recorded profile still requires its original filesystem locations. Supplying
paths makes those dependencies explicit; it does not qualify relocation or make
a public clone self-contained.

Create an ignored `work/carrier-float64-layer-runtime.json` containing only
`{"am_python":"<absolute path to the recorded interpreter>"}`. The existing
runner accepts executable paths in this file; data paths belong in the explicit
private-input manifest. Never commit the filled private manifest or raw arrays.

After the reviewed bundle is installed at
`parts/993-eng-carrier-0001/source/process-float64-20261107/` and the reviewed
recipe is installed at `manufacturing/workflows/993-carrier-float64-layer-v1.json`:

```sh
python3 scripts/run_part_workflow_v3.py run \
  manufacturing/workflows/993-carrier-float64-layer-v1.json \
  --runtime work/carrier-float64-layer-runtime.json \
  --output /absolute/private/output/current-layer-replay-001
```

The parent of the output must exist and the output must be fresh. The recipe
first runs a synthetic cube and four prewrite binding refusals, then the actual
current source. The part-specific guard retains the 300-second / 8-GiB RAM
limits, an 8-GiB free-space threshold, logs and exact owned-process cleanup.
The outer existing runner records recipe/source/output hashes.

The actual stage requires exact field names, shapes, dtypes and bytes against
the admitted direct layer-517 arrays, plus unchanged native and independent
domain audits. Strict exposure coverage remains unchanged. Recorded system and
loaded native-image identities must match; package presence alone is insufficient.

## Runtime and continuation limits

The existing PySLM installer and version lock remain available separately.
They pin the PySLM source revision and patch, but do not pin distribution-wheel
bytes or a Python patch version. A fresh install or another platform is a new
runtime qualification, not this same-profile replay. This draft does not install,
resolve, upgrade or qualify any package or Linux environment.

After this direct replay passes, migrate the already qualified full-calendar
driver and its source-bound output/continuation controls into a separate recipe.
Retain its exact all-index contract, golden worker check, byte cap, process guard
and volume arithmetic. Do not implement a second full-calendar algorithm or
silently expand this one-layer recipe. No supports or machine job are produced.
