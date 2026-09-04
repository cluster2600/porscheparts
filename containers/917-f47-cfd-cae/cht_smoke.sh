#!/usr/bin/env bash
set -eo pipefail
source /opt/openfoam14/etc/bashrc
set -u
root=$(mktemp -d /tmp/f47-cht.XXXXXX)
case "${root}" in /tmp/f47-cht.*) ;; *) exit 90 ;; esac
trap 'rm -rf -- "${root}"' EXIT
cp -a /opt/917-f47-cfd-cae/cht-fixture/. "${root}/"
cd "${root}"
foamDictionary system/controlDict -entry endTime -set 0.002 >/dev/null
foamDictionary system/controlDict -entry writeInterval -set 0.001 >/dev/null
blockMesh >blockMesh.log 2>&1
snappyHexMesh >snappyHexMesh.log 2>&1
splitMeshRegions -cellZones all -defaultRegion fluid >splitMeshRegions.log 2>&1
foamMultiRun >foamMultiRun.log 2>&1
grep -F 'End' foamMultiRun.log >/dev/null
grep -F 'fluid  time step continuity errors' foamMultiRun.log >/dev/null
test -d 0.002/fluid
test -d 0.002/metal
test -d 0.002/heater
printf '%s\n' '{"passed":true,"version":"OpenFOAM-14-foamMultiRun","fixture":"official_heatedDuct_shortened_to_two_steps","fluid_region":true,"solid_regions":2,"synthetic_fixture":true}'
