#!/bin/bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
test "$WM_PROJECT_VERSION" = v2406
test -d "$FOAM_LIBBIN"
export WM_PROJECT_DIR=/src
export WM_DIR=/src/wmake
export FOAM_SRC=/src/src
export FOAM_APPBIN=/out/bin
export PATH=/src/wmake:$PATH
mkdir -p /out/bin
printf 'compiler: '
g++ --version | head -n 1
dpkg-query -W -f='${Package} ${Version}\n' g++ make openfoam2406
sha256sum "$(command -v rhoPimpleFoam)"
cd /src/wmake/src
make
cd /src
wmakeLnIncludeAll
wmake -j1 applications/solvers/compressible/rhoPimpleFoam
sha256sum /out/bin/rhoPimpleFoam
