#!/bin/sh
set -eu
test "$(uname -m)" = x86_64
test "$(dotnet --version)" = 9.0.317
output=$(mktemp -d /tmp/station-smoke.XXXXXX)
trap 'rm -rf "$output"' EXIT HUP INT TERM
timeout 120 /usr/local/bin/station-picogk /opt/picogk-witness/bin/RuntimeWitness.dll "$output"
timeout 120 /opt/geometry-qa/bin/python /opt/picogk-witness/geometry-python-smoke.py
timeout 120 /opt/cad/bin/python /opt/station/cad-smoke.py
QT_QPA_PLATFORM=offscreen LD_LIBRARY_PATH=/opt/freecad/usr/lib timeout 120 /opt/freecad/usr/bin/python -c 'import sys; sys.path.append("/opt/freecad/usr/lib"); import FreeCAD, Part; assert Part.makeBox(10,20,30).Volume == 6000; print("FREECAD_CPU_PASS", FreeCAD.Version()[:3])'
command -v ccx
command -v gmsh
/opt/ovrtx-runtime/bin/python -c 'from importlib.metadata import version; assert version("ovrtx") == "0.3.0.312915"; print("OVRTX_INSTALLED_NOT_GPU_TESTED")'
test -x /usr/local/bin/vllm
bash -n /opt/qwen/start.sh
grep -q -- '--revision "$MODEL_REVISION"' /opt/qwen/start.sh
echo STATION_CPU_SMOKE_PASS
