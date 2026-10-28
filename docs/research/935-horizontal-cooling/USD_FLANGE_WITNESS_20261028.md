# 935 inspection assembly: PicoGK flange witnesses in USD

This checkpoint composes the eight lower-flange wall witnesses from the
[PicoGK scan-feature study](PICOGK_FLANGE_WITNESS_20261028.md) into the
[four-component inspection assembly](ORIGINAL_BOUND_ASSEMBLY_20261028.md).
The witness surfaces and the drive component share the exact source drive STL
hash `fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35`.
The eight additions are inspection annotations, not fasteners or a validated
mounting interface.

## Reproduce from the private inputs

The input directories are the accepted private native assembly, USD export,
and PicoGK flange witness receipts. The commands require macOS or another
environment capable of running the pinned inputs and Python USD bindings.
Use a fresh `work/` output directory for each run.

```bash
uv run --no-project --python 3.12 --with usd-core --with numpy==2.5.4 python \
  twins/935-horizontal-cooling-system-f0/source/compose_flange_witness_usd.py \
  work/935-original-bound-assembly-20261028/exports-002 \
  work/935-flange-witness-20261028/native-001 \
  work/935-usd-flange-witness-20261028/composed-NEW

uv run --no-project --python 3.12 --with usd-core --with numpy==2.5.4 \
  --with matplotlib==3.10.7 python \
  twins/935-horizontal-cooling-system-f0/source/render_flange_witness_context.py \
  work/935-original-bound-assembly-20261028/native-002 \
  work/935-usd-flange-witness-20261028/composed-NEW \
  work/935-usd-flange-witness-20261028/context-NEW
```

The compositor checks the original USD export hash, its four component IDs,
the exact drive STL, the PicoGK receipt, each of the eight witness STL hashes,
and their unverified-interface flags. It preserves the 417 MiB original USD
as a relative sublayer and authors eight magenta `UsdGeom.Mesh` prims under
`/World/inspection`. The composed USD is reopened; all 221,304 triangles,
face indices, and positions are checked against the source witness STLs after
conversion. The four base component identities remain present. The renderer
reads the composed USD and samples the original STL components to produce
XY/XZ full-assembly and flange-detail views; it is a visual review, not an
exhaustive surface-distance test.

## Accepted private result

The [private archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/935-root-repair-20261025)
contains `935-usd-flange-witness-20261028.tar.zst` and the standalone
`flange-witness-context.png`. Archive SHA-256:
`3bcbdbdc66ce71475a85e0f26ed3045152a24233df8e84acc1ca0a6ea8aaa34e`.
The accepted composed USD SHA-256 is
`5f330f4cf071e790b7c026a0ba1bb359c8c5dc19eef8003dfe12c94224bcbac9`;
the context image SHA-256 is
`46b94ea4bcf402a254161b784061fbdf7f5905c17ce77dc028699f80501c1596`.
The archive contains both USD layers, the composition report, the image, and
its render report. An earlier failed compositor output was rejected and is not
part of this accepted package.

The USD stage uses metres per unit and Z up. The source coordinates are still
**uncalibrated scan units**; multiplication by `0.001` is a recorded display
assumption, not proof that one source unit is one millimetre. The screenshot's
axes deliberately show source units. No exact 935 installation, mounting
clearance, engine compatibility, manufacturing release, or physical operation
has been verified. The next geometry gate is independent same-part calibration
and measured engine/drive mounting datums before fitment or load analysis.
