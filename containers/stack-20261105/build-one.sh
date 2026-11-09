#!/usr/bin/env bash
# Run from the allowlisted build-context root on the native Linux builder.
set -euo pipefail
name=${1:?image name required}
case "$name" in
  obj-metrology-f15|boundary-review-f23|warp-geometry|usd-brep|ov-libraries-cpu|scan-mesh-f17|cadsim|topology-context-f26|cad-author-f28|engine-cycle-f33|simready|recon|openfoam-engine-f35|mesh-cfd|gas-path-f38|air-oil-cycle-f34b|cae-reference-f31|simready-workflow|free-tools-cloudcompare|free-tools-salome|prusa-slicer|cae-integrated-f33|cae-aircooled-f34|917-engine-wave-f39|gmsh-mesh-f35|physicsnemo-cae-cu12|analysis-cgal-toolchain|analysis-cgal|m64-leap71|m64-leap71-native|fluidx3d-aircooled-f34|picogk-station-kit|picogk-m64|cad-recode-openclaw|cad-recode-cad|bionic-airflow-toolchain|vllm-runtime|jax-fem) ;;
  *) echo "Image not admitted to this build batch: $name" >&2; exit 2 ;;
esac
recipe="containers/stack-20261105/$name.Dockerfile"
tag="porscheparts/$name:stack-20261105"
receipts=${STACK_RECEIPTS:?absolute receipt directory required}
mkdir -p "$receipts"
run=$(mktemp -d "$receipts/$name.XXXXXX")
printf '%s\n' "$tag" > "$run/tag.txt"
sha256sum "$recipe" > "$run/recipe.sha256"
# The context is explicitly allowlisted before transfer. Wheel/deb artifacts are
# verified separately by their locks; retain hashes of all other source inputs.
find . -type f ! -path './wheelhouse/*' ! -path './debhouse/*' -print0 \
  | sort -z | xargs -0 sha256sum > "$run/context.sha256"
while read -r parent; do
  docker image inspect --format '{{.Id}} {{json .RepoDigests}}' "$parent"
done < <(awk '
  $1 == "FROM" && $2 ~ /^porscheparts\// {print $2}
  $1 == "COPY" && $2 ~ /^--from=porscheparts\// {sub(/^--from=/, "", $2); print $2}
' "$recipe" | sort -u) \
  > "$run/local-parent-images.txt"
date -u +%FT%TZ > "$run/started.txt"
build_args=()
if [ "$name" = picogk-station-kit ]; then
  test "${NVIDIA_EULA_ACCEPTED:-no}" = yes || {
    echo 'Kit requires the owner-authorized NVIDIA_EULA_ACCEPTED=yes' >&2
    exit 2
  }
  build_args+=(--build-arg NVIDIA_EULA_ACCEPTED=yes)
  printf '%s\n' 'Owner explicitly accepted NVIDIA terms on 2026-11-05.' > "$run/license-acceptance.txt"
fi
if [ -n "${STACK_PYTHON_BASE:-}" ]; then
  docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}}' "$STACK_PYTHON_BASE" > "$run/base-image.txt"
  build_args+=(--build-arg "PYTHON_BASE_IMAGE=$STACK_PYTHON_BASE")
fi
set +e
timeout 7200 docker build --network "${STACK_BUILD_NETWORK:-none}" "${build_args[@]}" --platform linux/amd64 --progress plain \
  --iidfile "$run/image-id.txt" -f "$recipe" -t "$tag" . > "$run/build.log" 2>&1
status=$?
set -e
printf '%s\n' "$status" > "$run/build-exit-code.txt"
if [ "$status" -eq 0 ]; then
  docker image inspect --format '{{.Id}} {{.Os}}/{{.Architecture}} {{.Size}}' "$tag" > "$run/image.txt"
  set +e
  case "$name" in
    cad-recode-openclaw)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /bin/sh "$tag" -ec 'openclaw --version; openclaw config validate' > "$run/smoke.log" 2>&1 ;;
    picogk-m64)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" /usr/local/bin/smoke-test.sh picogk-m64 > "$run/smoke.log" 2>&1 ;;
    cae-integrated-f33|cae-aircooled-f34)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /bin/bash "$tag" -ec 'python /opt/stack/gmsh-volume-smoke.py; python /opt/stack/ccx-smoke.py /tmp/ccx-runtime-smoke; cat /tmp/ccx-runtime-smoke/checks.json; openfoam-engine-f35-smoke' > "$run/smoke.log" 2>&1 ;;
    free-tools-cloudcompare)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" controls --output /tmp/control > "$run/smoke.log" 2>&1 ;;
    free-tools-salome)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" controls --units mm --output /tmp/control > "$run/smoke.log" 2>&1 ;;
    mesh-cfd)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /bin/bash "$tag" -ec 'python /opt/stack/mesh-cfd-smoke.py; blender --background --factory-startup --python-expr "import bpy; assert bpy.app.version[:3] == (5, 2, 3)"' > "$run/smoke.log" 2>&1 ;;
    recon)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /bin/bash "$tag" -ec 'colmap -h >/dev/null; glomap -h >/dev/null; blender --background --factory-startup --python-expr "import bpy; assert bpy.app.version[:3] == (5, 2, 3)"; python -c "import open3d, pymeshlab, cv2, trimesh, manifold3d, meshio"' > "$run/smoke.log" 2>&1 ;;
    simready|simready-workflow)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /usr/local/bin/simready-smoke "$tag" > "$run/smoke.log" 2>&1 ;;
    cadsim)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g --entrypoint /bin/bash "$tag" -ec 'python /opt/stack/cadsim-smoke.py; python /opt/stack/ccx-smoke.py /tmp/ccx-runtime-smoke; cat /tmp/ccx-runtime-smoke/checks.json' > "$run/smoke.log" 2>&1 ;;
    warp-geometry)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" --device cpu --output /tmp/report.json --samples 256 --repeats 2 > "$run/smoke.log" 2>&1 ;;
    usd-brep)
      timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" /opt/usd_brep_smoke.py --output /tmp/usd-brep > "$run/smoke.log" 2>&1 ;;
    *) timeout 300 docker run --rm --network none --cpus 2 --memory 4g "$tag" > "$run/smoke.log" 2>&1 ;;
  esac
  status=$?
  set -e
  printf '%s\n' "$status" > "$run/smoke-exit-code.txt"
fi
date -u +%FT%TZ > "$run/finished.txt"
printf '%s\n' "$run"
exit "$status"
