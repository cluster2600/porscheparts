#!/bin/sh
# Build and run the PicoGK monocoque in the m64-leap71 native image.
#   docker build -f containers/m64-leap71/Dockerfile.native -t porscheparts-picogk-native:dev containers/m64-leap71
#   sh run.sh [voxel-mm]
set -e
cd "$(dirname "$0")"
docker run --rm --memory=10g --memory-swap=10g --cpus=8 -v "$PWD:/w" -w /w \
  --entrypoint sh porscheparts-picogk-native:dev -c "
  mkdir -p /tmp/p && cp -r ZesadMonocoque.csproj src /tmp/p &&
  dotnet build /tmp/p/ZesadMonocoque.csproj -c Release -o /tmp/bin -p:UpstreamRoot=/upstream -nologo -v q &&
  cp /app/picogk.26.2.so /tmp/bin/ && dotnet /tmp/bin/ZesadMonocoque.dll work work ${1:-2.5};
  status=\$?; chown -R $(id -u):$(id -g) work; exit \$status"
