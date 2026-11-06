# PicoGK dashboard-trim concept

This folder belongs to `993-INT-DASHBOARD-TRIM-0001`: the visible trim covering
the 993 dashboard cross member. It is separate from the structural dashboard
panel `993 502 027 02` and from the small DT-01 switch blank.

The current `picogk.json` selects a bionic topology study. Its density field,
region tiles and base STL live in ignored `parts/picogk-catalog/out/` paths, so
the published study mesh cannot be rebuilt from a fresh clone by running the
catalogue command alone. `build_picogk_concept.py` selects the tracked
`DashboardTrim.cs` base generator with the **same numeric parameters** and
writes a new F0 mesh, report, logs and source-hash manifest under `work/`.
It does not change the catalogue record or any published mesh or image.
The [complete dashboard F0 inventory](../../../twins/993-dashboard-f0/README.md)
records the other components and interfaces; this trim mesh is not placed in
that assembly.

From the repository root on a native Linux filesystem, with the qualified
PicoGK checkout available:

```bash
PICO_ROOT="$HOME/picogk"
source "$PICO_ROOT/env.sh"
"$PICO_ROOT/run-capped.sh" -m 8G python3 \
  parts/993-int-dashboard-trim-0001/source/build_picogk_concept.py \
  --output work/dashboard-trim-f0-new
```

Choose a fresh output directory for every run. The script uses the catalogue's
machine-wide PicoGK lock. The STL is a **visual concept**, not a print file:
the 1,350 × 120 × 60 mm envelope, surface, vents, opening and ribs are design
assumptions. It has no measured clip-nut holes, knee-protection-strip anchors,
host clearance or passenger-airbag interface. The recorded vehicle-width
figure is an upper bound only, not a dashboard dimension.

For a small visualization STL, use the local Python environment with NumPy,
Trimesh, PyVista and VTK, and give the exporter a new path under `work/`:

```bash
"$HOME/.venvs/picogk-tools/bin/python3" \
  parts/993-int-dashboard-trim-0001/source/export_visual_mesh.py \
  --input work/dashboard-trim-f0-new \
  --output work/dashboard-trim-f0-new/dashboard-trim-f0-visual.stl
```

The exporter checks the build hashes, removes degenerate faces, reduces the
mesh to 18,000 triangles and checks topology, bounds and volume before writing
the STL and its JSON report. The checked [visual mesh](../../../twins/993-dashboard-f0/dashboard-trim-f0-visual.stl)
is an isolated view asset. Mesh closure does not establish any interface or
material qualification.

The scoped candidate variants in the part record are M564 and RS cars
documented without a passenger airbag. The PET note in the same record puts
`993 552 055/056 00` in a passenger-airbag illustration, so their mapping to
M564 is unresolved; **do not use those part numbers as an established M564
identity**. M562 is excluded. M561 requires direct passenger-side verification
and a separate scope decision. The existing
[`evidence/measurement-plan.md`](../evidence/measurement-plan.md) calls for
D01–D14 in place and after removal, three readings each, three bare-part
weighings, a licensed scaled surface capture and independent host datums.
Without those inputs, no fitted, functional or safety status is available.
