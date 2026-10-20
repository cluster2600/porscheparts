# Reproduce the 20 October reinforcement surface study

[Results, images and workflow](../../../../../docs/reports/carrier-resume-20261020/README.md)

This recipe reproduces the two certified patch meshes and the one-build-item
3MF assembly from repository inputs. The parent is revision 24af0584. These
are study files; the new volume mesh, mechanics and full print preparation
remain open. Historical scripts and refused input meshes are retained for
traceability. Use **`certified-patch-*.stl`** for the current assembly.

Run from the repository root with a fresh Python environment:

```sh
python3 -m venv work/carrier-resume-env
work/carrier-resume-env/bin/python -m pip install -r parts/993-eng-carrier-0001/source/design-20261016/resume-20261020/requirements-3mf.txt
```

Pinning is intentional: the assembly program rejects other dependency versions.
The installation command is provided for a new machine; this run reused an
already installed runtime. Use a fresh output directory for each execution.

```sh
CARRIER_SOURCE=parts/993-eng-carrier-0001/source/design-20261016/resume-20261020
CARRIER_PYTHON=work/carrier-resume-env/bin/python

$CARRIER_PYTHON "$CARRIER_SOURCE/bounded_patch_tessellation.py" \
  --control-nets "$CARRIER_SOURCE/inputs/nurbs-control-nets.json" \
  --output work/carrier-replay-bounded

$CARRIER_PYTHON "$CARRIER_SOURCE/certified_patch_collapse.py" \
  --meshes work/carrier-replay-bounded/patch-0.stl work/carrier-replay-bounded/patch-1.stl \
  --bounds work/carrier-replay-bounded/assessment.json \
  --output work/carrier-replay-cleaned

$CARRIER_PYTHON "$CARRIER_SOURCE/rebuild_component_3mf.py" \
  --baseline parts/993-eng-carrier-0001/source/design-20261016/corner-slide-candidate-20261018/candidate-surface.stl \
  --patches work/carrier-replay-cleaned/patch-0.stl work/carrier-replay-cleaned/patch-1.stl \
  --manifest "$CARRIER_SOURCE/certified-component-inputs.json" \
  --output work/carrier-replay-assembly
```

The assembly command checks all three source hashes, retains exact coordinate
and triangle bytes in exact-decimal 3MF XML, reopens the file with strict
lib3mf, checks the component graph and transforms, checks positive overlaps
and evaluates the nominal mass bound. `assessment.json` records each result.
Pass the manifest explicitly: the older default bounded-mesh manifest belongs
to the historical pre-contraction trial.

The [full independent audit](../../../../../docs/reports/carrier-resume-20261020/evidence/component-libigl-certified-001/assessment.json)
is a separate executed stage. Its
[exact Docker command](../../../../../docs/reports/carrier-resume-20261020/evidence/component-libigl-certified-001/plan.json)
records the pinned image, ownership, input mounts, read-only filesystem,
resource bounds and time limit. Replace the old absolute host paths with the
new checkout/output paths and use a **fresh** output, container name and CID
file. The worker `audit_component_meshes.py` expects:

| Container path | Read-only input |
| :--- | :--- |
| `/input/study.3mf` | Actual generated archive |
| `/input/source-assessment.json` | Matching assembly `assessment.json` |
| `/source/worker.py` | `audit_component_meshes.py` from this directory |
| `/source/audit.py` | `parts/993-eng-carrier-0001/source/remesh-20261016/audit.py` |
| `/output` | Fresh writable audit directory |

The worker verifies the archive and complete component byte identities before
running all-facet checks. Its process exit means the audit completed; acceptance
requires `status == "all_complete_component_surface_screens_passed"` in the
final report. Refused geometric results are deliberately saved too.

`readback_native_control_nets.py --inputs .../inputs --output FRESH_DIRECTORY`
reopens the two saved native BREP patches with build123d 0.11.1 /
cadquery-ocp-novtk 7.9.3.1.1. It compares every tensor coefficient to the input
control nets; it does not run a new Boolean operation.

`render_resume.py --root . --output FRESH_DIRECTORY` renders every retained
parent triangle and the certified patches with Matplotlib 3.10.8. The saved
figure provenance lists input hashes and plotting versions.

Focused source and evidence tests:

```sh
python3 -m unittest discover -s tests -p 'test_carrier_*20261020.py'
```

Run `make check` for repository integration. It is broader than this recipe
and requires the repository's supported test runtime and retained datasets.
