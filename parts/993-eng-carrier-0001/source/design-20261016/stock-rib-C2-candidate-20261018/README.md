# Outward-C2 rib candidate: geometry and editable source

This handover provides the **actually reproduced** `stock-outward-C2-rib-width-v1` candidate, with a native mass of **1.274798 kg**, editable construction sources and local commands for fresh outputs. One bounded run from these delivered sources reproduced both the generated body and the admitted master byte for byte, together with all 12 window and four modified-rail rows. [Actual reproduction](evidence/reproduction/summary.json) and its [independent review](evidence/reproduction/root-terminal-review-001.json) retain the complete comparison identities. Native BREP is the master. Units are millimetres.

| File | Actual role | SHA-256 |
| --- | --- | --- |
| `candidate-native.brep` | Native master: one valid solid, 236 faces, 721 edges, 478 vertices, no degenerated edges | `d64a7faf8455735e05198661be823ead7037c23b58d36522e1cca60056aea624` |
| `candidate-default.step` | Default STEP exchange: both fresh strict native differences were valid and empty in all dimensions | `97d281f838b1b659bc10221584726da13db0f963d6408d486e62ae6f9f2447ff` |
| `candidate-surface.stl` | Dedicated Gmsh surface: 597,720 triangles; whole topology and sampled two-way surface checks passed | `17d7de30d5d6e2ef51fee4c1dac9da66ad618bcfeda4cf61fe90e084a807d7b2` |

The measured adaptive native volume is **288,415.83655452315 mm³**, giving **1.2747979975709924 kg** at 4,420 kg/m³. The separate nonadaptive F/F/F volume is **288,415.8744573265 mm³**; it is the comparable operator for Gmsh import-volume checks. The STEP adaptive relative volume difference was **5.980736572652745 × 10⁻⁹**, below the retained `1e-8` guard. These operators remain separate in the complete records under `evidence/body` and `evidence/STEP`.

The source increases only the four mirrored outward-Y rib rails over |X| = 22–35 mm. The fixed addition is `2.8 * 64*t^3*(1-t)^3` mm, with zero endpoint position, first-derivative and second-derivative changes. The original inner rail and cutters remain. The first-window opening inset is 2.8 mm, and the other window branches use 1.5 mm. The complete 12-row window ledgers and four actual modified-rail rows are retained under `evidence/trial`. This is an opening inset, not a wall-thickness measurement.

The new candidate has its own closed native retention, surface, complete protected study-interface and STEP results. The compact current d64 mesh and coarse mechanical ROOT reviews are included under `evidence/mesh` and `evidence/mechanics`; raw fields remain external. These numerical results are not a CAD strength conclusion or a convergence result. The filename remains `candidate`; no catalogue status is changed by this handover.

## Editable files and dependencies

`generator/build_stock.py` is the actual construction entry point and accepts one output-directory argument. `generator/corrected_cad.py` contains the exact degree-6 outward rail poles (`outer_Q`). `generator/normal-builder/cad.py` contains the actual first-window branch override. The ordinary geometry/material settings and sleeve plan are in `payload/parts/993-eng-carrier-0001/source/design-20261016/{bounded-webs.json,bounded-webs-plan.json}`. The nominal JSON alone does not encode the two source overrides; retain the source and ledgers together.

Only the two `SOURCE` assignments in the entry point and private correction builder are rebased to the delivered `payload` tree. Every function body is unchanged. `source-rebase.json` and the original sources under `original-source` give the complete reversible replacements. The original correction helper is also delivered under `payload/.../correction-20261013/corrected_cad.py`: the unchanged normal builder imports its `precise_volume` through the original import path. It is distinct from the private rib construction module.

The payload includes the unchanged interface-study JSON and all five files it hashes. Its `ROOT = SOURCE.parents[4]` resolves to the payload root. These are the retained study-interface inputs. The existing Python 3.10 runtimes remain external: build123d 0.11.1, the installed OCP package 7.9.3.1.1, NumPy 2.0.2 for CAD, and Gmsh 4.15.2 for dedicated surfaces. `dependencies/external-runtime.json` preserves their original complete runtime byte map, interpreter aliases and source-context path/hash. Package metadata and the available build123d licence are copied; no runtime binary is bundled. Repository material uses the included `LICENSE`; external packages retain their own licences.

The following commands require this repository's installed runtimes at the documented paths. They are a local reproduction recipe, not a self-contained portable runtime. Changing source or parameters creates a new candidate and requires its own checks. The first two steps have been executed once from these rebased sources, with both original BREP hashes equal. The complete four-step manual recipe was not rerun as one campaign; the stored STEP and dedicated STL retain their separate closed checks.

## 1. Run the original generator into a fresh directory

From the repository root, set `CAPSULE` to this handover directory and choose a new `OUT`. The delivered directory is `parts/993-eng-carrier-0001/source/design-20261016/stock-rib-C2-candidate-20261018`.

```sh
REPO="$PWD"
CAPSULE="$REPO/parts/993-eng-carrier-0001/source/design-20261016/stock-rib-C2-candidate-20261018"
OUT="$REPO/work/carrier-stock-rib-C2-reproduced-001"
test ! -e "$OUT" || exit 1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
"$REPO/work/part-workflow/runtimes/design-standalone/bin/python" -I -B -c \
  'import runpy,sys;sys.path.insert(0,sys.argv[1]);sys.argv=sys.argv[2:];runpy.run_path(sys.argv[0],run_name="__main__")' \
  "$REPO/work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages" \
  "$CAPSULE/generator/build_stock.py" "$OUT/regenerated-stock"
```

The generator creates `regenerated-stock` and the sibling `regenerated-stock-without-sleeves`. It retains its validity, single-solid, adaptive STEP readback, mass and bounds checks. It also emits construction STEP/STL files; that coarse construction STL is distinct from the dedicated surface delivered above.

## 2. Preserve the actual import/export master step

The admitted master was obtained by importing and re-exporting the generated `native-body.brep`, exactly as in the actual trial. The original generated body was **b95c165967bac9a22cdeae768141ca713d6930d92c2d3cdaf59987666080fc67** (2,072,739 bytes); the admitted master was **d64a7faf…** (2,072,735 bytes). These are separate byte identities.

```sh
"$REPO/work/part-workflow/runtimes/design-standalone/bin/python" -I -B -c \
  'import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from OCP.OSD import OSD_ThreadPool;OSD_ThreadPool.DefaultPool_s().Init(1);from build123d import import_brep,export_brep;out=Path(sys.argv[2]);candidate=import_brep(out/"regenerated-stock/native-body.brep");raw=out/"candidate-native.brep";assert not raw.exists();export_brep(candidate,raw)' \
  "$REPO/work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages" "$OUT"
```

Compare both fresh BREP hashes with `provenance.json`. A mismatch remains a mismatch; no byte-exact or native-equivalence result is inferred from successful construction. The closed strict containment checks and protected results apply to the stored d64 master, not automatically to a new run.

## 3. Default STEP and dedicated surface commands

To export the fresh master with the same default writer call (no writer keyword changes):

```sh
"$REPO/work/part-workflow/runtimes/design-standalone/bin/python" -I -B -c \
  'import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from OCP.OSD import OSD_ThreadPool;OSD_ThreadPool.DefaultPool_s().Init(1);from build123d import import_brep,export_step;out=Path(sys.argv[2]);target=out/"candidate-default.step";assert not target.exists();body=import_brep(out/"candidate-native.brep");export_step(body,target)' \
  "$REPO/work/part-workflow/runtimes/cad-base/lib/python3.10/site-packages" "$OUT"
```

For a new dedicated STL, use the delivered unchanged worker. Obtain the actual new master hash first; the worker checks it before import. Its output directory must be fresh.

```sh
MASTER_SHA=$(shasum -a 256 "$OUT/candidate-native.brep" | cut -d ' ' -f 1)
"$REPO/work/part-workflow/runtimes/geometry-standalone/bin/python" -I -B \
  "$CAPSULE/recipe/gmsh_brep_remesh.py" \
  "$OUT/candidate-native.brep" "$OUT/surface" \
  --expected-brep-sha256 "$MASTER_SHA" --minimum-size-mm 0.25
```

The worker retains Gmsh's 2 native threads, minimum 0.25 mm, maximum 3 mm, curvature 96, algorithm 6, order 1 and smoothing 0. It emits STL, MSH and `meshing.json`. Export and meshing commands reproduce operations; a fresh result needs the separate original readback, two-way surface and protected-interface checks. Exact current commands and their roles are also retained in `commands.json`.

## Stored evidence and future reproduction

`evidence` contains the seven actual independent ROOT closures plus complete selected scientific records. They establish the stored files' provenance and scoped checks. Full owner runtime pin maps, numerical FEA fields and runtime binaries remain at the external repository paths and hashes listed in `provenance.json` and `dependencies/external-runtime.json`. They are not silently claimed to be present in this compact bundle.

The actual two-step reproduction closed RC0 under the original 600-second owned supervisor, 560-second child alarm and CPU 520/540 bounds. It matched generated `b95c1659…` and canonical `d64a7faf…` in full bytes. The complete source/runtime maps, all fresh files and process cleanup were independently checked. No additional audit loop or equivalence fallback was used.

See the [current nominal interface sheet](../../../../../docs/media/carrier-nominal-interfaces-20261018/README.md) for the retained model coordinates, and the [current numerical checkpoint](../../../../../docs/reports/carrier-rib-20261018/README.md) for this d64 candidate's actual mesh and mechanical results. These linked documents and installed runtimes remain repository dependencies.
