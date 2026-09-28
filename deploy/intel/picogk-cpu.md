# Kali1 PicoGK CPU worker

Kali1 executes the existing station C# geometry with a private portable runtime.
The installed bundle is `~/station-cpu-runner-20260928-r8kj70sz/runtime`.
Kali2 invokes `kali1-picogk JOB --span-mm 50 --voxel-mm 0.25`, then verifies the
collected files under `~/stations/kali1/JOB/`. The SSH backhaul on Kali2 port
2221 depends on the controller Mac. No gateway restart is needed.

Each calculation is limited to two CPU equivalents, 2 GiB RAM, no swap,
128 tasks and 300 seconds, at nice level 10. A nonblocking lock prevents two
worker jobs from overlapping. Output directories must be new. The calculation
proves software geometry only; it does not perform metal qualification.

## Recreate the runtime on Kali2

Use the final station image already available in Kali2 Docker. The following
commands copy only .NET runtime 9.0.19, the native PicoGK library, compiled
programs, sources and licences. They never run Docker on Kali1. The image tag
is prepared for publication; verify its identity before extracting.

Run from a repository checkout on Kali2:

```sh
set -eu
umask 077
image=ghcr.io/cluster2600/3dprinting993-picogk-m64:station-20260928-persistent-4f58a4e28ab7
test "$(docker image inspect --format '{{.Id}}' "$image")" = sha256:4f58a4e28ab7706e7735b2185123c2d8fd6eb94a3d1842a9e352950ce503bdfb
bundle="$PWD/work/kali1-picogk-runtime"
test ! -e "$bundle"
mkdir -p "$bundle/dotnet/shared" "$bundle/native" "$bundle/source" "$bundle/licenses"
container=$(docker create "$image")
trap 'docker rm "$container" >/dev/null' EXIT
docker cp "$container:/usr/share/dotnet/dotnet" "$bundle/dotnet/"
docker cp "$container:/usr/share/dotnet/host" "$bundle/dotnet/"
docker cp "$container:/usr/share/dotnet/shared/Microsoft.NETCore.App" "$bundle/dotnet/shared/"
docker cp "$container:/app/picogk.26.2.so" "$bundle/native/"
docker cp "$container:/opt/picogk-native/lib" "$bundle/native/"
docker cp "$container:/opt/picogk-witness/bin" "$bundle/witness"
docker cp "$container:/opt/station-demo/bin" "$bundle/demo"
docker cp "$container:/opt/picogk-witness/RuntimeWitness.cs" "$bundle/source/"
docker cp "$container:/opt/picogk-witness/RuntimeWitness.csproj" "$bundle/source/"
docker cp "$container:/opt/station-repo/twins/picogk-station-demo/Program.cs" "$bundle/source/"
docker cp "$container:/opt/station-repo/twins/picogk-station-demo/StationDemo.csproj" "$bundle/source/"
docker cp "$container:/opt/provenance/sources.lock" "$bundle/source/"
docker cp "$container:/usr/share/dotnet/LICENSE.txt" "$bundle/licenses/dotnet-LICENSE.txt"
docker cp "$container:/usr/share/dotnet/ThirdPartyNotices.txt" "$bundle/licenses/dotnet-ThirdPartyNotices.txt"
docker cp "$container:/upstream/PicoGK/LICENSE" "$bundle/licenses/PicoGK-LICENSE"
cp twins/picogk-station-demo/qualification/runtime/kali1-cpu/bundle-manifest.json "$bundle/"
```

The [221 file hashes](../../twins/picogk-station-demo/qualification/runtime/kali1-cpu/bundle-manifest.json)
were originally extracted from image `fd50c61399fd…`; all 221 were then
[compared with the final image](../../twins/picogk-station-demo/qualification/runtime/kali1-cpu/final-image-equivalence.json)
and found identical. The archive hash describes the original transfer archive;
the runner checks each extracted file independently, so tar metadata does not
need to reproduce that archive hash.

Transfer this directory and [run-picogk-cpu.sh](run-picogk-cpu.sh) over verified
SSH into a new private staging directory on Kali1. The launcher already
installed on Kali2 is [kali1-picogk.py](kali1-picogk.py); its fixed remote path
matches the installed bundle. On Kali1, the native invocation is:

```sh
bash ~/station-cpu-runner-20260928-r8kj70sz/run-picogk-cpu.sh \
  ~/station-cpu-runner-20260928-r8kj70sz/runtime \
  ~/station-cpu-runner-20260928-r8kj70sz/results/coupon-new 50 0.25
```

The [qualification receipts](../../twins/picogk-station-demo/qualification/runtime/kali1-cpu/summary.json)
include the measured cgroup limits, geometry reports, service continuity and
Kali2 launch/collection. Native SSH generated the dedicated client key on Kali2;
only its public part was installed with `restrict` on Kali1. No private key,
credential file, system package or user checkout was copied or altered.
