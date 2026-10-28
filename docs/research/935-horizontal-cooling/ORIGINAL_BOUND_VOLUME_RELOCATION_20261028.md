# 935 original-export-bounded fluid volume: Gmsh node relocation

This experiment starts from the best 0.005 repaired-wall fluid mesh in the
[facet sweep](ORIGINAL_BOUND_FACET_SWEEP_20261028.md). The mesh is bounded by
the original PicoGK **export**, not by a calibrated historical 935 scan.
Its SHA-256 is
`0f6d5cadd5b48c3345e8440c5a881018ca463b005641c46e0b376d9ecbcd8bb7`.
The duct and conditional 1 source unit = 1 mm conversion are unchanged.

Gmsh 4.15.2 `Relocate3D` was run with `force=False` from that same input,
once with one iteration and once with five iterations. An independent audit
checked every wall triangle and marker against the pinned PLC, tetrahedral
orientation and mean-ratio quality. Both runs preserved the four boundary
triangle coordinate sets, all 984,724 nodes and 4,651,098 tetrahedra, with
no zero or negative-volume tetrahedra. Maximum surface-node displacement
was below `1e-16 m`.

| Mesh | Mean ratio < 0.01 | Mean ratio < 0.05 | Minimum mean ratio | CFD decision |
|---|---:|---:|---:|---|
| Pinned input | 1,426 | 1,954 | 0.00004215 | rejected |
| `Relocate3D`, one iteration | 1,402 | 1,688 | 0.00004215 | rejected |
| `Relocate3D`, five iterations | 1,402 | 1,690 | 0.00004215 | rejected |

The one-iteration output SHA-256 is
`726449bb01f037046bd7a20e028bc15b0df3a0e2d46faad91b1375815880cd8f`;
the five-iteration output SHA-256 is
`0684dfc276c9058e5a099ab8ff1520aca0da686b78f6ff4c6faebf56697fafe6`.
The one-iteration result improves the counts slightly, but five iterations
do not improve the strict count further. The unchanged minimum quality and
remaining near-wall weak cells keep both volumes outside the CFD gate.
No pressure, flow or torque result is inferred from either volume.

The [private evidence archive](https://github.com/cluster2600/porscheparts-935-private/releases/download/935-root-repair-20261025/935-fluid-relocate-20261028.tar.zst)
contains both output meshes, receipts, logs and independent audits. Its
SHA-256 is
`759d5b5d743a150c6227275bf61e0c3dc36aa33d055cbcd2954f70e3b7b17d9e`;
the local archive integrity check and the private release digest agree.

Run from the repository root with a fresh private directory under `work/`:

```sh
src=twins/935-horizontal-cooling-system-f0/source/gmsh-fluid-study-20261028
plc=work/935-original-bound-facet-sweep-20261028/prepared-005/boundary.npz
mesh=work/935-original-bound-facet-sweep-20261028/prepared-005/gmsh-volume/fluid.msh
out=work/935-fluid-relocate-20261028/relocate-001
uv run --no-project --python 3.12 --with gmsh==4.15.2 \
  python "$src/relocate_original_bound_fluid.py" "$mesh" "$out" --iterations 1
uv run --no-project --python 3.12 --with gmsh==4.15.2 \
  --with numpy==2.5.4 --with scipy==1.18.1 \
  python "$src/audit_fluid.py" "$plc" "$out/fluid.msh" "$out/audit.json"
```

Repeat with `--iterations 5` and a fresh `relocate-005` directory. The
output mesh and audit contain private geometry and stay outside public Git.
The next volume experiment needs a change to the near-wall tetrahedral
topology, followed by native OpenFOAM `checkMesh` before any CFD run.
