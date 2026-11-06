# DDK and photograph guided PicoGK display, revision 2

This source authors original F0 display surfaces from editable `scene.json` descriptors. The complete visible-family inventory uses PicoGK implicit surfaces: rounded panels, variable-section lofts, rings, disks and short capsule marks. Photos guide qualitative component hierarchy and appearance. Every section, radius, angle and location remains an artistic assumption in `visual_stage_not_vehicle`; none is a vehicle measurement or a functional interface.

The source is separate from the hash-pinned original and photo-v1 generators. It does not import or alter their STL. The shallow glovebox, low side vents with vertical blades, integrated instrument brow, rounded lower band and sloping tunnel console follow the observations linked in [the reference register](../ddk-study-v2/references.json). The DDK example is RHD and does not establish the target M564/LHD configuration. Gauge marks and needles are symbolic geometry, not a calibrated instrument or an OEM face reproduction.

`KNEE_STRIP_RESERVED` names an assumed visible zone, not a selected physical knee-trim variant. `DEFROST_OUTLETS_AND_DUCTS` contains only top outlet marks, not inferred ducts. No mounting feature, restraint part, measured hole pattern, fastener or vehicle assembly transform is generated. Separate display meshes may overlap; the output is not a printable assembly.

## Reproduction

Run from a native Linux checkout with the local PicoGK runtime and .NET 9. `Program.cs` is self-contained; its project explicitly includes only that source. Choose a new `work/` output directory on every run.

```sh
cd /home/maxime/porscheparts
source /home/maxime/picogk/env.sh
dotnet build twins/993-dashboard-f0/ddk-source-v2/DashboardDdkStudy.csproj -c Release -p:PicoGKAssembly=/home/maxime/picogk/smoke/bin/PicoGK.dll -v:q
python3 - <<'PY'
from runpy import run_path
import subprocess

catalogue = run_path('parts/picogk-catalog/tools/run_part.py')
catalogue['acquire']()
try:
    subprocess.run([
        '/home/maxime/picogk/run-capped.sh', '-m', '8G', 'dotnet',
        'twins/993-dashboard-f0/ddk-source-v2/bin/Release/net9.0/DashboardDdkStudy.dll',
        'twins/993-dashboard-f0/ddk-source-v2/scene.json',
        'work/993-dashboard-ddk-f0-v2-reproduction-01',
    ], check=True)
finally:
    catalogue['LOCK'].unlink(missing_ok=True)
PY
source /home/maxime/.venvs/picogk-tools/bin/activate
python3 twins/993-dashboard-f0/ddk-source-v2/render_scene.py --report work/993-dashboard-ddk-f0-v2-reproduction-01/scene-report.json
```

Generation is bounded to an unused private directory under `work/` and the catalogue lock is released even if generation fails. It writes twelve separate STL families plus a receipt binding source, project and scene hashes. The renderer verifies those hashes and every raw mesh hash, then writes front and three-quarter PNGs plus a sidecar binding the reference register, renderer, generator, project and scene. Raw mesh output stays ignored; only selected PNGs and receipts are published in [the study](../ddk-study-v2/README.md).

Rendering requires NumPy, PyVista/VTK and Pillow. The sidecar records versions, source and loaded triangle counts, zero-area faces, camera vectors and pixel sizes. These checks verify reproducibility and display integrity; they do not establish physical accuracy or qualification. No source photograph is redistributed.
