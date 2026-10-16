# Adamantine stress export regression

This small benchmark compiles the real upstream `source/PostProcessor.cc` and
calls both public export paths. It checks the 3D von Mises invariant and the
coupled export directory. It does not compile the full thermo-mechanical solver
or validate an LPBF process or a part.

`PostProcessor.patch` changes two sites in the selected upstream revision:

- Use xz for the third shear term; yz was counted twice and xz omitted.
- Read `output_dir` in the coupled constructor, matching the single-physics
  constructor.

The shared private stress getter has one caller, `mechanical_dataout`; both
`write_mechanical_output` and coupled `write_output` reach it. The change keeps
the public API and field names. Historical outputs are not rewritten.

## Sources and licence

[upstream.json](upstream.json) pins the repository, archive, source and dependency
image. The source revision is
[`3990489a10902912889617856f6e2e097d52a412`](https://github.com/adamantine-sim/adamantine/tree/3990489a10902912889617856f6e2e097d52a412).
The original archive SHA-256 is
`c3be270cda7c1be74b966b45d1aa7a271fc5d5c5a60f61da29690c68ddc02575`.
Upstream code and patch context retain **Apache-2.0 WITH LLVM-exception**;
[LICENSE.upstream](LICENSE.upstream) is the unchanged upstream licence. The C++
harness retains its SPDX notice. Other original repository material follows the
[root licence](../../LICENSE).

No full upstream source tree or solver binary is vendored. The author image
`rombur/adamantine@sha256:a7c394fb9075ea8343f0ed1734574a5d158563e6f2b71894cdcc9f5f75d6e4d9`
provides build dependencies, including deal.II 9.6.2. Its embedded source is
`5aca53eeb1048884be54fb48864e9ff6cb9f9b71`, a different revision. The commands
below compile the explicitly downloaded **3990489a** source with the patch;
they do not run the image's bundled solver. Allow sufficient disk space for
this large dependency image.

## Reproduce the native regression

Prerequisites: Linux x86_64, Docker, CMake and a C++17 compiler with deal.II 9.6
built with MPI, P4EST and Kokkos. The pinned author image supplies these native
dependencies. NumPy and meshio are optional Python dependencies needed only for
the independent exported-field checker.

From the repository root, prepare a new scratch directory outside the checkout:

```sh
benchmark="$PWD/benchmarks/lpbf-adamantine-export"
scratch="$(mktemp -d)"
cd "$scratch"
curl --fail --location https://codeload.github.com/adamantine-sim/adamantine/tar.gz/3990489a10902912889617856f6e2e097d52a412 --output upstream.tar.gz
printf '%s  %s\n' c3be270cda7c1be74b966b45d1aa7a271fc5d5c5a60f61da29690c68ddc02575 upstream.tar.gz | sha256sum --check
mkdir original
tar --extract --gzip --file upstream.tar.gz --directory original --strip-components=1
cp -a original fixed
patch --directory fixed --strip=1 < "$benchmark/PostProcessor.patch"
printf '%s  %s\n' 09be78633f5a04934bbcd420c884f3c3202d99715a6119b22daf094683ca3506 fixed/source/PostProcessor.cc | sha256sum --check
```

Run the minimal native build and CTest in the pinned dependency image. The
benchmark mount is read-only; build files and synthetic fields stay in scratch.
Run CTest once per fresh build directory: its output-directory refusal prevents
silent overwrites of existing evidence.

```sh
docker run --rm --interactive --platform linux/amd64 --network none \
  --cpus 2 --memory 4g --pids-limit 128 \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$benchmark,dst=/benchmark,readonly" \
  --mount "type=bind,src=$scratch,dst=/work" \
  --workdir /work --entrypoint /bin/bash \
  rombur/adamantine@sha256:a7c394fb9075ea8343f0ed1734574a5d158563e6f2b71894cdcc9f5f75d6e4d9 -s <<'SH'
set -eu
cmake -S /benchmark -B /work/build-fixed -DADAMANTINE_SOURCE_DIR=/work/fixed -DDEAL_II_DIR=/opt/dealii -DCMAKE_BUILD_TYPE=Release
cmake --build /work/build-fixed --parallel 2
ctest --test-dir /work/build-fixed --output-on-failure
SH
```

For a system with the native dependencies already installed, use the same
three CMake/CTest commands with local paths. `ADAMANTINE_SOURCE_DIR` is mandatory
and must refer to the external source tree.

Read the actual CTest VTUs with the independent invariant checker:

```sh
python3 -m venv "$scratch/checker-env"
"$scratch/checker-env/bin/python" -m pip install numpy meshio
"$scratch/checker-env/bin/python" "$benchmark/tests/test_check_exports.py"
"$scratch/checker-env/bin/python" "$benchmark/tests/check_exports.py" "$scratch/build-fixed/ctest-output" --report "$scratch/assessment-fixed.json"
```

The checker report must contain **16 passed cases**, eight through each public
export path: pure xy/xz/yz shear, non-hydrostatic diagonal stress, hydrostatic
stress, a mixed tensor, negative xz shear and the mean of two quadrature-point
invariants. The independent reference uses the complete tensor deviator,
`sqrt(1.5 * sum(s_ij * s_ij))`. The last case checks the current export
convention: mean of the pointwise invariants, rather than invariant of the
mean tensor. The `2e-7` relative and absolute tolerances account for Float32 VTU
output; they do not measure Float64 mechanical-solver accuracy.

To reproduce the original failure, build the same benchmark in a separate new
directory with `-DADAMANTINE_SOURCE_DIR=/work/original`. Run its executable from
a dedicated scratch working directory. The original native executable returns
1 when the coupled exporter ignores `output_dir`; its eight mechanical VTUs
also expose the xz/yz errors. Keep this expected failure separate from the
corrected run. An exporter regression success alone does not establish that
the full solver builds or runs.

## Shared thermal-elastic control

[coupon/contract.json](coupon/contract.json) and its
[Adamantine](coupon/common.info)/[CalculiX](coupon/common.inp) inputs define a
hypothetical **12 × 4 × 6 mm** one-element control: constant linear elasticity,
a clamped bottom face, otherwise traction-free and adiabatic boundaries, and
uniform volumetric heating from 300 K to 301 K in two 5 ms increments. The
reference is exact within this single Q1 element, obtained by integrating its
strain energy; it is not an exact continuum solution.

At 301 K, the reference maximum displacement is 0.2404887776 µm and the cell
mean von Mises stress is 1,199,966.340575 Pa. Anisotropic dimensions give
unequal xz/yz shears; the original scalar formula instead gives
1,050,529.175983 Pa. The contract contains the reference nodal displacements
and all eight integration-point stress tensors.

The native CalculiX and corrected Adamantine research-profile controls both
completed. Final mean von Mises was 1,199,966.324810 Pa for CalculiX and
1,199,966.375 Pa for Adamantine: a **0.050190 Pa** difference. The
[execution report](../../docs/reports/LPBF_NATIVE_VERIFICATION_20261015.md)
records the profile and predeclared tolerances. The exporter harness does not
itself perform that solve. CalculiX's uncoupled transient mechanics and
Adamantine's quasistatic mechanics are distinct; each output was checked
against the exact static FE reference.

[coupon/observed-results.json](coupon/observed-results.json) publishes the
sanitised execution summary, predeclared limits and hashes of the actual
synthetic fields. [coupon/observed/adamantine](coupon/observed/adamantine)
contains the seven original PVD/PVTU/VTU files; the original
[CalculiX text output](coupon/observed/calculix-common.dat) contains nodal and
integration-point fields at 5 and 10 ms. CalculiX did not request a time-zero
output frame; its 300 K initial condition is identified as input, not observed
data. The Adamantine XML files preserve their original internal `/work/`
references. For local inspection, read the VTU files directly or map their leaf
filenames to this observed directory. No private host paths or addresses are
included.

No powder, melting, deposition, plasticity, build supports, cutoff or qualified
manufacturing data are represented. This control does not replace the earlier
rejected mesh-convergence study.

## Reproduce the coupled research profile

The separately named `research-build-profile.patch` reduces expensive template
instantiations to 3D, one material and constant polynomial properties. Its CLI
guard rejects 2D, multiple materials, nonconstant properties, table input,
device memory and ensembles. The lightweight 2D helper instantiations remain
available because upstream helpers require them. The three phase families,
FE degrees 1–5 and both quadratures remain compiled; only **Solid, FE1, Gauss,
constant properties** were exercised by this coupon. This is a research build,
not verification of every upstream capability.

Apply this additional patch to the already corrected source. It does not
include `PostProcessor.cc`, which is covered by the production patch above:

```sh
cd "$scratch"
patch --directory fixed --strip=1 < "$benchmark/research-build-profile.patch"
docker run --rm --interactive --platform linux/amd64 --network none \
  --cpus 2 --memory 4g --pids-limit 128 \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$benchmark,dst=/benchmark,readonly" \
  --mount "type=bind,src=$scratch,dst=/work" \
  --workdir /work --entrypoint /bin/bash \
  rombur/adamantine@sha256:a7c394fb9075ea8343f0ed1734574a5d158563e6f2b71894cdcc9f5f75d6e4d9 -s <<'SH'
set -eu
c++ -std=c++17 -O0 -I/work/fixed/application /benchmark/tests/test_profile_guard.cc -o /work/profile-guard-test
/work/profile-guard-test
cmake -S /work/fixed -B /work/build-solver -DDEAL_II_DIR=/opt/dealii -DCMAKE_BUILD_TYPE=Release -DADAMANTINE_ENABLE_ADIAK=OFF -DADAMANTINE_ENABLE_CALIPER=OFF
cmake --build /work/build-solver --target adamantine --parallel 2
mkdir /work/coupon-output
/work/build-solver/bin/adamantine --input-file /benchmark/coupon/common.info --output-dir /work/coupon-output
SH
```

The guard must print `Profile guard passed: supported profile and six rejection
cases`. The solver must return 0 **and** log `Simulation done`; a zero return
code alone is insufficient because the upstream CLI can return 0 after some
input-validation errors. Require three frames at 0, 0.005 and 0.01 s and read
the actual T/U/stress fields. The report defines their absolute acceptance
limits. Preserve logs, source/profile hashes, binary hash and raw outputs.
The existing upstream CMake build is reused; no replacement solver or generic
job runner is introduced here.
