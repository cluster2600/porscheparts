#!/bin/sh
set -eu
# Run only inside the pinned amd64 PicoGK image. No private head is required.
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test_parent=${1:-/workspace}
test_root=$(mktemp -d "$test_parent/picogk-cooling-regression.XXXXXX")
dotnet build "$source_dir/CoolingDomains.csproj" -c Release \
  -o "$test_root/bin" -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false
dotnet /opt/picogk-witness/bin/RuntimeWitness.dll "$test_root/primitive"
dotnet "$test_root/bin/CoolingDomains.dll" \
  "$test_root/primitive/sphere-radius5mm-voxel0.5mm.stl" "$test_root/domains" 0.6
printf 'PICOGK_COOLING_NATIVE_REGRESSION_PASS %s\n' "$test_root"
# Keep the small synthetic artifacts and complete witness report as evidence.
