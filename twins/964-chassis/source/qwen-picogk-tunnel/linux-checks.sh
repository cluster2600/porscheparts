#!/usr/bin/env bash
# Run only in the pinned, network-disabled container documented in README.md.
set -euo pipefail
cd /input
sha256sum --check --quiet manifest.sha256
test ! -e /output/legacy
test ! -e /output/bin
export DOTNET_CLI_HOME=/tmp/dotnet-cli
export DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export NUGET_PACKAGES=/tmp/nuget
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1
export LD_LIBRARY_PATH=/app:/opt/picogk-native/lib

dotnet build /input/source/twins/964-chassis/source/qwen-picogk-tunnel/Tunnel.csproj \
  -c Release -p:PicoGKPath=/opt/station-demo/bin/PicoGK.dll \
  -p:BaseIntermediateOutputPath=/output/obj/ -o /output/bin
for pitch in 4 2; do
  dotnet /output/bin/Tunnel.dll /input/inference/input.json \
    "/output/native-${pitch}mm" "$pitch"
done

# Run the old truss only in a new output copy; never overwrite historical evidence.
cp -R /input/legacy /output/legacy
cd /output/legacy
python3 twins/993-carbon-safety-cell/source/build_structural_screening.py --write
python3 twins/993-carbon-safety-cell/source/build_structural_screening.py --check
cd twins/993-carbon-safety-cell/derived
ccx -i selected-torsion
cd /output/legacy
python3 twins/993-carbon-safety-cell/source/verify_calculix.py --solver-version 2.21
