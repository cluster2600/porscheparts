#!/bin/bash
# Compare unmodified numerical sources with one Fortran storage flag changed.
set -euo pipefail
ulimit -v 4194304
CARRIER_CONTEXT=$1
CARRIER_BUILD=/workspace/carrier-compiler-20261022
test ! -e "$CARRIER_BUILD"
mkdir -p "$CARRIER_BUILD/output"
apt-get -s install --no-install-recommends libspooles-dev libarpack2-dev liblapack-dev patch > "$CARRIER_BUILD/dependency-simulation.txt"
python3 - "$CARRIER_BUILD/dependency-simulation.txt" <<'PY'
import re,sys
from pathlib import Path
changed=lambda line:re.match(r'^Inst \S+ \[',line)is not None
assert not changed('Inst new-package (1.0 Ubuntu [amd64])')
assert changed('Inst existing-package [1.0] (2.0 Ubuntu [amd64])')
if any(changed(line)for line in Path(sys.argv[1]).read_text().splitlines()):raise ValueError('Existing runtime package changes refused during active solves')
PY
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends libspooles-dev libarpack2-dev liblapack-dev patch > "$CARRIER_BUILD/apt-install.log" 2>&1
python3 - "$CARRIER_CONTEXT" "$CARRIER_BUILD" <<'PY'
import hashlib,json,sys,tarfile
from pathlib import Path
context,base=map(Path,sys.argv[1:]);archives={'calculix-ccx_2.21.orig.tar.bz2':'51d229aee320cf685216d360f7c04f9a57af0148fbe840483a964c86c315da82','calculix-ccx_2.21-1.debian.tar.xz':'6c2a934b66491c9e916cbf6328167d417f7e985b380e200facf92c3e953d255f'}
for name,digest in archives.items():
 path=context/name
 if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Pinned source archive differs')
 destination=base/'static'if name.endswith('.bz2')else base/'static/CalculiX'
 destination.mkdir(parents=True,exist_ok=True)
 with tarfile.open(path)as archive:archive.extractall(destination,filter='data')
(base/'output/archive-identities.json').write_text(json.dumps(archives,indent=2)+'\n')
PY
while IFS= read -r CARRIER_PATCH; do
    patch -d "$CARRIER_BUILD/static/CalculiX" -p1 < "$CARRIER_BUILD/static/CalculiX/debian/patches/$CARRIER_PATCH"
done < "$CARRIER_BUILD/static/CalculiX/debian/patches/series"
cp -a "$CARRIER_BUILD/static" "$CARRIER_BUILD/recursive"
for CARRIER_PROFILE in static recursive; do
    CARRIER_FFLAGS='-O2 -fallow-argument-mismatch'
    if test "$CARRIER_PROFILE" = recursive; then CARRIER_FFLAGS="$CARRIER_FFLAGS -frecursive"; fi
    printf '%s\n' "$CARRIER_FFLAGS" > "$CARRIER_BUILD/output/$CARRIER_PROFILE-fflags.txt"
    make -C "$CARRIER_BUILD/$CARRIER_PROFILE/CalculiX/ccx_2.21/src" -j2 CC=gcc FC=gfortran-13 \
        'CFLAGS=-Wall -O2 -I/usr/include/spooles -DARCH="Linux" -DSPOOLES -DARPACK -DMATRIXSTORAGE -DUSE_MT=1' \
        "FFLAGS=$CARRIER_FFLAGS" > "$CARRIER_BUILD/$CARRIER_PROFILE-build.log" 2>&1
    cp "$CARRIER_BUILD/$CARRIER_PROFILE/CalculiX/ccx_2.21/src/ccx_2.21" "$CARRIER_BUILD/output/ccx-$CARRIER_PROFILE"
    ldd "$CARRIER_BUILD/output/ccx-$CARRIER_PROFILE" > "$CARRIER_BUILD/output/$CARRIER_PROFILE-linked-libraries.txt"
done
sha256sum "$CARRIER_BUILD/output/ccx-static" "$CARRIER_BUILD/output/ccx-recursive" /usr/bin/ccx > "$CARRIER_BUILD/output/binary-identities.txt"
gcc --version > "$CARRIER_BUILD/output/gcc-version.txt"
gfortran-13 --version > "$CARRIER_BUILD/output/gfortran-version.txt"
cp "$CARRIER_BUILD/static/CalculiX/debian/copyright" "$CARRIER_BUILD/output/copyright-debian.txt"
