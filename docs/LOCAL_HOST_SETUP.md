# Local host setup

How to set up a Linux or WSL2 workstation to run the checks, the native PicoGK
geometry and the heavy local jobs. The tool choices themselves are in
[TOOLCHAIN.md](TOOLCHAIN.md), the stack and its execution status in
[SOFTWARE_STACK.md](SOFTWARE_STACK.md), the container images in
[CONTAINER_INDEX.md](CONTAINER_INDEX.md) and
[COMPUTE_ENVIRONMENT.md](COMPUTE_ENVIRONMENT.md).

Everything below was observed on the maintainer's WSL2 host (Ubuntu, 15 GB RAM,
Intel Iris Xe) between October and November 2026. Versions are what that host
ran. For evidence, record the exact versions and image IDs of each run in its
report, never this page.

## 1. Clone onto a native Linux file system

Clone to ext4, for example `/home/<user>/porscheparts`. **Not** a WSL DrvFs mount
such as `/mnt/c/...`. Several tools publish through directory-descriptor
renames that DrvFs does not serve correctly, and they then fail closed for an
environment reason (see "Repository location" in [AGENTS.md](../AGENTS.md)). The
full suite also runs about six times slower there.

## 2. Run the same checks as CI

On Debian/Ubuntu, install Gmsh's native libraries first:
`sudo apt-get install --no-install-recommends libgl1 libglu1-mesa`.
The catalogue CI installs these before the Python requirements.

```bash
make check-setup   # installs the CI dependency versions into .venv-check/ (needs uv)
make check
```

- Setup also installs the same hash-pinned native geometry oracle as CI.
- The system `python3` usually lacks NumPy. Use `.venv-check/bin/python` to run
  a check script or a single test module directly:
  `.venv-check/bin/python -m unittest discover -s tests -p 'test_<name>.py'`.
  `pytest` is not installed.
- The link checker (`scripts/check_doc_links.py`) only counts files git tracks.
  `git add` new files before `make check`, or links to them report as broken.

### Skips and test counts depend on the environment

- Tests that need an optional tool (PicoGK native, `pxr`, Cantera, a private
  output) skip when it is absent. CI allows at most `max_skips` from
  [tests/skip-budget.json](../tests/skip-budget.json), enforced only where
  `SKIP_BUDGET_ENFORCE=1` (the `validate.yml` workflow).
- The shared requirements include Trimesh, Rtree and NetworkX for synthetic scan topology
  and surface-distance checks. Adding them enabled 22 existing 935 tests and
  removed 78 skips across the full suite. Shapely 2.2.0 additionally enables
  polygon coverage and constrained-triangulation checks: 5,902 tests pass with
  252 skips. Headless OCP 7.9.3.1.1 then enables 79 more native geometry
  checks: the same 5,902 tests pass with 173 skips. USD 25.11 and Gmsh
  4.15.2 then enable 35 more checks: 5,902 tests pass with 138 skips, lowering
  the budget to 140.
  Five repair tests still require
  the separately pinned, patched PySLM runtime; Shapely alone cannot run them.
  Older WSL environments produced
  416–421 skips; refresh dependencies before comparing with the current budget.
  A local count above the budget is not by itself a regression. A new skip
  **in a test you added** is: CI will count it.
- Some test modules define more tests when optional dependencies exist. For
  example, the bionic-turbo modules run 82 tests in `.venv-check` and 109 in the
  `3dprinting993-cadsim:dev` container.
- A few process-control tests (signal handling in
  `tests/test_935_interwalk_admission.py`) are timing-sensitive and can fail
  when the machine is saturated. Rerun the module alone before treating it as
  a failure.

Cantera remains in the dedicated F33 image. A native macOS arm64 installation
of the same Cantera 3.2.0 version failed three exact report comparisons against
the frozen F33 evidence, with differences in the last floating-point digits.
The version string alone does not reproduce that image's arithmetic. The
shared requirements therefore do not install it, and the frozen report and
exact replay assertions remain unchanged.

## 3. Heavy jobs on a shared or WSL host

A voxel field, mesher or solver that outgrows memory can take the whole WSL VM
down. Rules that have held:

- **Cap every heavy job:**
  `systemd-run --user --scope -q -p MemoryMax=8G -p MemorySwapMax=0 <command>`.
  Exit code `137` means the job hit the cap. It is not a solver verdict.
- **One full `make check` at a time.** Serialise runs through a lock, cap them
  and give each its own log:

  ```bash
  flock /tmp/porscheparts-makecheck.lock \
    systemd-run --user --scope -q -p MemoryMax=5G -p MemorySwapMax=0 \
    env "PATH=$PWD/.venv-check/bin:$PATH" make check > /tmp/makecheck-<branch>.log 2>&1
  ```

  Quote the `PATH=` assignment: the WSL `PATH` contains Windows directories with
  spaces. Use a **unique log name per run**. A shared name lets queued runs
  truncate each other's log, because the `>` redirection happens before `flock`
  acquires the lock.
- **Never run two capped heavy containers whose caps together exceed host
  memory.** Run one part at a time.
- **Worktrees are full checkouts** (about 4 GB here). Remove those whose branch
  is merged (`git worktree remove`, then `git worktree prune`) before the disk
  fills. A full disk makes `git worktree add` fail half-way.

## 4. Native PicoGK on Linux or WSL

New geometry is written in C# on PicoGK ([ADR 0017](decisions/0017-picogk-new-geometry.md)).
The container route is in `containers/m64-leap71/` and pins its sources in
[`containers/m64-leap71/sources.lock`](../containers/m64-leap71/sources.lock).
A host install, which is faster to iterate on and needed for the viewer, works
like this:

1. **.NET 9 SDK** in user space (`dotnet-install.sh --channel 9.0`), with
   `DOTNET_ROOT` and `PATH` set.
2. **Sources:** clone PicoGK, PicoGKRuntime, LEAP71_ShapeKernel and
   LEAP71_LatticeLibrary into one directory and export it as `UpstreamRoot`.
   The project files reference `$(UpstreamRoot)/PicoGK/PicoGK.csproj` and
   default to `/upstream` when the variable is unset, so either export it or
   build with `dotnet build -p:UpstreamRoot=$HOME/<dir>`. Host clones may be
   newer than `sources.lock`, so record the commits used in each report.
3. **Native runtime.** Building PicoGKRuntime from source takes hours
   (about 3 h at `-j3`; `-j8` thrashes under a 10 GB cap). Instead, build
   `containers/m64-leap71/Dockerfile.native`
   (`docker build -f containers/m64-leap71/Dockerfile.native -t porscheparts-picogk-native:dev containers/m64-leap71`).
   Then copy `/app/picogk.26.2.so` out of it (`docker create`, `docker cp`),
   together with the shared libraries it needs that the host lacks
   (`libtbb.so.12`, `libblosc.so.1`, `liblz4.so.1`, `libsnappy.so.1`,
   `libzstd.so.1` from the image's `/usr/lib/x86_64-linux-gnu`). Put them in one
   directory on `LD_LIBRARY_PATH` and check with `ldd picogk.26.2.so`. Record
   the image ID (`docker image inspect --format '{{.Id}}'`) as the runtime
   identity in reports.
4. **Graphics on WSLg:** `export GALLIUM_DRIVER=d3d12`. Without it Mesa falls
   back to llvmpipe: every step is about 3× slower, and the viewer dies with
   `GLX BadAccess`.
5. **Headless use:** construct `new Library(voxelSizeMm)` and pass a log path
   (`new LogFile(path)` or `Library.Go(..., logPath)`). The default log goes to
   `~/Documents/PicoGK.log` and crashes if that folder does not exist.
6. Run heavy voxel jobs under a memory cap (section 3).

Keep these exports in a small `env.sh` and source it from your shell profile.
A host install is a convenience. A result counts only with the runtime
identity, sources and settings recorded beside it, as the evidence rules of
[AGENTS.md](../AGENTS.md) require.
