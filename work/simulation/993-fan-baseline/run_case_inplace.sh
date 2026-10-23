#!/bin/bash
# In-container runner (invoked by run_case.sh). OpenFOAM v2312.
# bash WITHOUT `set -u`: OpenFOAM bashrc dereferences unset vars.
CASE="${1:?}"
cd "/work/$CASE"
. /usr/lib/openfoam/openfoam2312/etc/bashrc
echo "== versions"
echo "WM_PROJECT_VERSION=$WM_PROJECT_VERSION"
echo "== blockMesh"
blockMesh > blockMesh.log 2>&1; echo "exit=$?"; tail -2 blockMesh.log
echo "== blockMesh -overwrite (mesh to constant/polyMesh)"
blockMesh -overwrite > blockMeshOverwrite.log 2>&1; echo "exit=$?"; tail -2 blockMeshOverwrite.log
echo "== topoSet (discCells)"
topoSet > topoSet.log 2>&1; echo "exit=$?"; grep -E "cellSet" topoSet.log | tail -2
echo "== checkMesh"
checkMesh > checkMesh.log 2>&1; echo "exit=$?"; grep -E "cells:|nodes:|faces:|Mesh OK|FAILED|Max skewness|Max grid non-orthogonality|Max aspect ratio|Mesh non-orthogonality" checkMesh.log
echo "== simpleFoam"
simpleFoam > simpleFoam.log 2>&1; rc=$?
echo "simpleFoam exit=$rc"
echo "== final state"
grep -E "^Time = " simpleFoam.log | tail -1
grep -E "average\(outlet\)" simpleFoam.log | tail -1
grep -E "Solving for|continuity" simpleFoam.log | tail -8
exit $rc
