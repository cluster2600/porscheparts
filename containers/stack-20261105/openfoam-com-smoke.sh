#!/usr/bin/env bash
set -o pipefail
source /usr/lib/openfoam/openfoam2606/etc/bashrc
set -e
test "$WM_PROJECT_VERSION" = v2606
case_dir=$(mktemp -d /tmp/openfoam-cavity.XXXXXX)
trap 'rm -rf "$case_dir"' EXIT
cp -a "$FOAM_TUTORIALS/incompressible/icoFoam/cavity/cavity/." "$case_dir/"
cd "$case_dir"
blockMesh > log.blockMesh 2>&1
checkMesh > log.checkMesh 2>&1
grep -q 'Mesh OK' log.checkMesh
icoFoam > log.icoFoam 2>&1
grep -qx End log.icoFoam
test -s 0.5/U
test -s 0.5/p
echo OPENFOAM_COM_2606_CAVITY_CPU_PASS
