#!/bin/bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
test "$WM_PROJECT_VERSION" = v2406
test -d "$FOAM_LIBBIN"
test -f /native/OpenFOAM-v2406/META-INFO/api-info
export WM_PROJECT_DIR=/native/OpenFOAM-v2406
export WM_DIR=/native/OpenFOAM-v2406/wmake
export FOAM_SRC=/native/OpenFOAM-v2406/src
export FOAM_APPBIN=/out/bin
export PATH=/native/OpenFOAM-v2406/wmake:$PATH
mkdir -p /out/bin
g++ --version | head -n 1
dpkg-query -W -f='${Package} ${Version}\n' g++ make openfoam2406
sha256sum "$(command -v rhoPimpleFoam)"
cd /native/OpenFOAM-v2406/wmake/src
make
cd /native/OpenFOAM-v2406
wmakeLnIncludeAll
test -e /native/OpenFOAM-v2406/src/OpenFOAM/lnInclude/Time.H
test ! -e /native/OpenFOAM-v2406/src/OpenFOAM/lnInclude/time.h
wmake -j1 applications/solvers/compressible/rhoPimpleFoam
sha256sum /out/bin/rhoPimpleFoam
