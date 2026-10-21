# Figure 25 — the C1 junction at the window boundary

This drawing shows actual CAD section profiles before and after the C1 fillet,
in one common oblique plane. The plane contains the native normal ray at the
foot associated with the **coarse-mesh peak, element 84037/IP1**, and the Z axis.
The horizontal U and vertical Z axes are metric and share the same limits in
both panels. The R1 fillet is an intersection of the existing three-dimensional
BREP master; it is not a circular arc redrawn in the picture.

[PNG](carrier-C1-jonction-coupe-oblique.png) ·
[SVG](carrier-C1-jonction-coupe-oblique.svg) ·
[PDF](carrier-C1-jonction-coupe-oblique.pdf)

The orange ray enters native face 60 and leaves face 62 after a reported local
chord of **0.08651954398105025 mm**; it re-enters face 68 at
W = 0.2650828520317755 mm. These are local junction observations, not a whole-wall
or global minimum-thickness measurement. The later H2 maximum is 90371/IP2 at a
different position and is **not plotted** in this plane. No stress field,
convergence claim or new mechanical result is produced by this picture.

All 29 section edges before and 30 after are retained as complete sampled XYZ
profiles and submitted to the drawing; cropping affects display only. The
0.001 mm curve-sampling deflection is a drawing setting, not a CAD-fidelity
certificate. The native C1 BREP and baseline STEP parents are identified by
their original hashes in the data and evidence; neither large CAD parent is
included here. The C1 STEP exchange remains **refused**. The master and its
mechanical evidence are retained separately in the
[native-C1 capsule](../../design-20261016/native-C1-20261017/README.md).

## Actual drawing and replay evidence

Native extraction003 produced 29/30 profiles without changing the CAD. Its first
render returned 0 but root refused publication because lower labels overlapped;
the source, exports and refusal remain under [history/layout003](history/layout003/root-render-terminal-review-001.json).
Presentation004 changes only the bottom subplot margin from 0.25 to 0.31. Root
viewed the actual004 PNG and PDF and approved the separated labels. The original
producer003 and presentation004 remain distinct, with SHA-identical sources and
profiles under `sources/mirror/`.

The [actual portable replay](verification/root-terminal-review-001.json) ran once
from `/`, returned 0, reaped its child and closed its owned process group. All
**11 complete deterministic render-receipt fields**, including status, and the
whole PNG/SVG/PDF bytes equal004. It took 2.451159s overall; the drawing itself
took 1.855747s, with peak RSS 142393344 bytes. No CAD extraction, meshing, mechanical
solver or geometry operation was rerun.

The frozen 31-file [mirror manifest](sources/manifest.json), tested
[replay source](sources/replay.py), [declared closure rebase](sources/historical_closure.py),
plans, commands, logs and owned receipts are included unchanged. The four path
substitutions are recorded in [the exact diff](sources/closure-from-003.diff).
They read the copied original producer/export-plan bytes while retaining the
historical command, output paths and complete source maps. They do not rewrite
or relabel the old execution. Preparation001 and its missing-status comparison
remain historical; portable002 adds status and the corresponding refusal test.

`archive.json` inventories every file in this capsule except itself, with size,
full SHA and the origin of each copied file. The integrity checker needs only
Python's standard library and does not load the plotting or CAD runtime:

```sh
python3 -I -B parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-junction-section-20261017/verify.py
python3 -I -B parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-junction-section-20261017/selfcheck.py
```

## Reproduce the sampled-point drawing

The replay requires the **same 219 installed plotting-runtime files at their
recorded absolute paths and hashes**: Python, NumPy, Matplotlib, Pillow and the
selected font. They are not bundled. They are checked before/after drawing, and
the renderer recaptures scientific imports after all three exports. This is not
a cross-host runtime rebase, an offline installation recipe or a native CAD
reproduction. The original CAD/runtime source maps describe the historical
extraction; the drawing replay does not read those external CAD dependencies.

From the repository, choose new, absent plan and output paths. The following
creates a new plan by adapting deployment paths only; historical paths, source
bytes, all profiles, runtime authority and expected export hashes stay fixed.
The archived GO is retained as execution provenance, not an authorization for
unrelated work.

```sh
python3 - <<'PYPLAN'
from pathlib import Path
import hashlib, json
repo = Path.cwd().resolve()
cap = repo / 'parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-junction-section-20261017'
plan = json.loads((cap / 'verification/plan-001.json').read_text())
mirror = cap / 'sources/mirror'
p003 = mirror / 'work/carrier-C1-junction-section-figure-003'
p004 = mirror / 'work/carrier-C1-junction-section-figure-004'
plan['capsule_root'] = str(mirror)
plan['manifest'] = str(cap / 'sources/manifest.json')
plan['data'] = str(p003 / 'data-001/section-data.json')
plan['extraction_receipt'] = str(p003 / 'data-001/extraction-receipt.json')
plan['extraction_supervision'] = str(p003 / 'export-execution-001/execution-receipt.json')
plan['root_visual_QA'] = str(p004 / 'root-render-terminal-review-001.json')
plan['root_GO'] = str(cap / 'verification/root-review-GO-001.json')
plan['output_directory'] = str(repo / 'work/C1-junction-replay-NEW')
path = repo / 'work/C1-junction-replay-NEW-plan.json'
with path.open('x') as stream:
    json.dump(plan, stream, indent=2)
    stream.write('\n')
print(path)
print(hashlib.sha256(path.read_bytes()).hexdigest())
PYPLAN
```

Use the printed plan SHA and an absolute fresh output path below. The same
reviewed shim sets the drawing's current directory to `/`:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
/usr/bin/nice -n 10 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B -c \
  "import os,runpy,sys;os.chdir('/');sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name='__main__')" \
  /ABSOLUTE/REPOSITORY/parts/993-eng-carrier-0001/source/progress-figures-20261016/C1-junction-section-20261017/sources/replay.py \
  /ABSOLUTE/REPOSITORY/work/C1-junction-replay-NEW-plan.json NEW_PLAN_SHA \
  /ABSOLUTE/REPOSITORY/work/C1-junction-replay-NEW
```

The direct command retains the 95s alarm and CPU 90–100s limits. The historical
proof additionally used the [exact owned supervisor](verification/owned-supervision/work/carrier-process-20261017/source010-exposure-preflight-003/supervise.py)
with 120s total and 10+10s cleanup; the direct command does not silently recreate
that process-group supervision. A new owned campaign must rebind the existing
launch plan to the copied paths, complete hashes and fresh outputs under its
workspace, preserving its root/group guards. No new rebase framework is supplied.
