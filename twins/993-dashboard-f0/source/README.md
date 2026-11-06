# PicoGK dashboard visual scene

This source builds a schematic F0 display of a complete 993 dashboard. All coordinates and dimensions in `scene.json` are artistic display assumptions in `visual_stage_not_vehicle`, expressed in millimetres only to set render scale. No scan or measured vehicle transform is available. The resulting surfaces do not represent an installed, fitted, or manufacturable dashboard.

Run from a native Linux checkout of the repository with the local PicoGK runtime and .NET 9 available. On the qualified host:

```sh
cd /home/maxime/porscheparts
source /home/maxime/picogk/env.sh
dotnet build twins/993-dashboard-f0/source/DashboardVisualScene.csproj -c Release -p:PicoGKAssembly=/home/maxime/picogk/smoke/bin/PicoGK.dll -v:q
flock /tmp/picogk-catalog.lock /home/maxime/picogk/run-capped.sh -m 8G dotnet twins/993-dashboard-f0/source/bin/Release/net9.0/DashboardVisualScene.dll twins/993-dashboard-f0/source/scene.json work/993-dashboard-full-f0-local-01
python3 twins/993-dashboard-f0/source/render_scene.py --report work/993-dashboard-full-f0-local-01/scene-report.json
```

Choose a new `work/` output directory for every run. The generator writes separate STL display layers and `scene-report.json`; the renderer writes front and three-quarter PNGs with a provenance sidecar in `renders/`. PyVista and Pillow are required for the renderer. Generation occurs under ignored `work/`; selected 2D previews and receipts may be tracked in the twin, while raw scene meshes remain private. No combined printable assembly is exported.
