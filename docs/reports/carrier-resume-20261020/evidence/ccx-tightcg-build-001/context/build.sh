#!/bin/sh
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends build-essential gfortran libspooles-dev libarpack2-dev liblapack-dev python3 patch ca-certificates
mkdir /build
# Exact Debian snapshot archives are checked by the owner before this worker.
tar -xjf /source/calculix-ccx_2.21.orig.tar.bz2 --strip-components=1 -C /build
tar -xJf /source/calculix-ccx_2.21-1.debian.tar.xz -C /build
while IFS= read -r ccx_patch; do
    patch -d /build -p1 < "/build/debian/patches/$ccx_patch"
done < /build/debian/patches/series
python3 /source/tighten.py
make -C /build/ccx_2.21/src -j2 \
 'CFLAGS=-Wall -O2 -I/usr/include/spooles -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1' \
 'FFLAGS=-O2 -fallow-argument-mismatch'
install -m 755 /build/ccx_2.21/src/ccx_2.21 /usr/local/bin/ccx-tightcg
cp /usr/local/bin/ccx-tightcg /output/ccx-tightcg
cp /build/ccx_2.21/src/preiter.c /output/preiter-tightened.c
cp /build/debian/copyright /output/copyright-debian.txt
sha256sum /usr/local/bin/ccx-tightcg /usr/bin/ccx > /output/binary-identities.txt
ldd /usr/local/bin/ccx-tightcg > /output/linked-libraries.txt
dpkg-query -W -f='${Package} ${Version}\n' > /output/build-package-versions.txt
