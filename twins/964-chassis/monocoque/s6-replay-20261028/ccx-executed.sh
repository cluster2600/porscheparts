#!/bin/sh
set -eu
exec docker run --rm --name monocoque-s6-fine-20261028 --network none --cpus=2 --memory=12g --memory-swap=12g --pids-limit=128 --read-only --tmpfs /tmp:rw,size=128m --cap-drop ALL --security-opt no-new-privileges --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 --mount "type=bind,src=$PWD,dst=/work" --workdir /work --entrypoint /usr/bin/timeout sha256:c9772ae9223a4f800a3ceda77d2494e67e34c8526eb0f204b3c8e052266641b4 900 ccx "$@"
