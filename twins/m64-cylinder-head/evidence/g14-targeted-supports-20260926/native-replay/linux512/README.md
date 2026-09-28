# Linux build and reference qualification — prepared, not executed

This job builds CCX 2.21, SPOOLES 2.2 and static ARPACK-NG 3.9.1 from the
retained archives. It runs the retained analytical cube, then two exact -z
project-reference repeats and one +x control with a fresh Linux matrix and CPU
CG. It does not run the fine mesh, rent a machine or install host packages.

The prior job manifest names
`ghcr.io/cluster2600/3dprinting993-picogk-m64@sha256:7c7048431256c455d1396c2e71e38be15b6d0d5d035f41fdde03de47a9025ccd`.
Its Dockerfile starts from the pinned .NET SDK 9.0.317 Debian 12 image and
installs cmake/g++/Python. It does not establish the live rented image,
architecture or presence of gfortran/OpenBLAS. The controller must verify the
actual image digest and native x86_64 host before running this job.

Prerequisites: gcc, gfortran, cmake, make, ctest, patch, pkg-config, perl, ar,
ldd, OpenBLAS development library and Python with numpy==2.2.6,
scipy==1.14.1. Inspect the actual Linux package candidates, pin those exact
versions when installing and retain the package transaction. No compiler
version or availability is asserted here. The job captures versions,
Debian package inventory, binary and resolved dynamic-library SHA-256 values.

Transfer the paths in `inputs.json` preserving repository-relative layout,
plus these job files. Keep input files read-only to the worker where practical.
The output is a new exclusive subdirectory under this `linux512` directory.
Use an outer process-group timeout before the independently controlled billing
deadline; every child command also has a timeout. This job is not a billing guard.

```
python linux_job.py --repo /workspace/repo --output /workspace/repo/work/m64-g14/linux512/run-1 --check
python -m unittest test_linux_job -v
timeout --signal=TERM --kill-after=30 COMPUTE_SECONDS python -u linux_job.py --repo /workspace/repo --output /workspace/repo/work/m64-g14/linux512/run-1 --deadline COMPUTE_DEADLINE_EPOCH --image-ref VERIFIED_IMAGE_REF
```

The existing Linux G12 rejected field remains rejected (0.20572046% direct/CG
disagreement). A Mac reference pass cannot qualify this new Linux binary.
Only `summary.json` with complete/build/cube/reference all true qualifies the
new runtime for these reference cases. Fine-mesh convergence, hot material,
assembly, manufacturing and engine-start claims remain false.

CCX GPL-2.0, SPOOLES public-domain declaration and ARPACK-NG BSD licence remain
inside the unchanged retained archives and extracted source tree. The build
records their source hashes. Compatibility changes are the recorded recipe's
compiler path, Tree filename, ETree null argument and CCX header declarations;
the I2Ohash numerical change is exactly the reviewed three integer products.
