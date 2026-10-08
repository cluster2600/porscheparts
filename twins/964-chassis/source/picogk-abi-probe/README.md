# Kali execution and PicoGK diagnosis — October 2, 2026

This rerun executes computations, without qualifying a shell or a process.
The [receipt](../../derived/kali-compute-20261002.json) separates the successful
runs, the failures and the digests. No raw scan, Qwen weights, secret,
shared container or historical evidence was modified.

## Computations executed

- **Kali 1, native Python**: eight architectures of the historical F1 truss,
  source at commit `135dcc8ef6e71ac483e1ed3036217536562c80a1`.
- **Kali 2, Docker**: the same truss, then CalculiX 2.21 on the regenerated deck.
  The Python outputs and the deck are identical across machines. The retained
  numerical stiffness remains 21,011.7 Nm/deg; CalculiX/Python deviation:
  `7.817523457564439e-7` relative, below the existing threshold `1e-4`.
- **Kali 2, PicoGK**: rerun of the tunnel at 4 and 2 mm with the earlier Qwen
  inputs, with no new inference. See the receipt for the native results
  and the Mac/Linux deviations, which do not constitute a manufacturing tolerance.
- **Kali 2, existing mesh-cfd image**: the 15 F37 tests blocked on the Mac's
  Docker socket pass. They test an LPBF tool of the 917 program, not the
  manufacturing of the carbon monocoque.

With the candidate DLL, the three initial interferences are found at both
resolutions and the probes for the openings and walls pass. The maximum
Mac/Linux deviation of the non-zero intersection volumes is 0.166% at 4 mm and
0.0174% at 2 mm. The subtraction leaves a zero residual on the same grid, still
with zero additional clearance. No general convergence is established.

Docker responds on Kali 2. The SSH account on Kali 1 does not belong to the
Docker socket group and `sudo -n` asks for a password; no permission was
changed. The native Python computations on Kali 1 do not need it.

The global check remains not green: the local target
`make 917-f46-vast-controller-check` hits the historical digest mismatch
of the Vast connector again. No historical report is rewritten to hide it.
The full global suite was not rerun on Kali in this rerun.
The seven local tests `test_964_*.py`, `bash -n` on the launcher and
`git diff --check` pass; the builds of the candidate, the probe and
the tunnel have no errors or warnings.

## Linux defect reproduced and isolated fix

The first tar transfer introduced `._Program.cs`, macOS metadata that the
compiler took for C#. The next transfer uses
`COPYFILE_DISABLE=1 tar --no-xattrs --exclude='._*'` into a new directory.
The first failure and its log are kept.

With the initial PicoGK DLL, `Voxels.bIsInside` also returns `true` for the
two points outside the reference cylinder. The same native function with a
return explicitly marshaled as one byte gives the three expected answers.
The initial declaration does not specify this size. This diagnosis
is consistent with the distinction between the C++ `bool` and the .NET boolean
marshaled by default described by [Microsoft](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/best-practices#boolean-parameters-and-fields).

`bool-return.patch` only adds `[return: MarshalAs(UnmanagedType.I1)]`
to this declaration, in a **build copy**. The candidate DLL is
built offline from the sources contained in the image, then mounted
only in the computation container. The image, the DLL installed on Kali,
the tunnel program and the initial Mac results remain unchanged.

The same `[return: MarshalAs(UnmanagedType.I1)]` fix was already recorded on
main on 2026-09-07 as
[`twins/m64-cylinder-head/source/picogk-cooling/patches/picogk-0e6cf6b-bIsInside-I1.patch`](../../../m64-cylinder-head/source/picogk-cooling/patches/picogk-0e6cf6b-bIsInside-I1.patch);
this probe confirms it independently on Linux.

`Program.cs` is the executable regression test: non-zero exit code
with the initial binding, zero with the candidate. It compares one interior point
and two exterior points far from the surface. This test and the tunnel probes
do **not qualify all PicoGK APIs**, nor all native booleans.
The candidate is a profile of this study, not a global update.

## Reproduction in the existing image

Station image, immutable local ID:
`sha256:4f58a4e28ab7706e7735b2185123c2d8fd6eb94a3d1842a9e352950ce503bdfb`.
F37 image:
`sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696`.
No download or cloud launch. Non-root containers, no network,
read-only root filesystem, capabilities dropped; 2 CPUs, 2 GiB without swap,
128 processes, stop at 600 seconds for the tunnel run.

Mount this directory at `/source:ro` and a new directory at `/output`. With
`DOTNET_CLI_HOME=/tmp/dotnet`, `NUGET_PACKAGES=/tmp/nuget` and
`LD_LIBRARY_PATH=/app:/opt/picogk-native/lib`, run in the image:

```sh
mkdir /output/runtime-source
cp /upstream/PicoGK/Internals/Interop.cs /output/runtime-source/Interop.cs
cd /output/runtime-source
patch --fuzz=0 < /source/bool-return.patch
dotnet build /source/PicoGK.Candidate.csproj -c Release \
  -p:BaseIntermediateOutputPath=/output/runtime-obj/ -o /output/runtime-bin
dotnet build /source/Probe.csproj -c Release \
  -p:PicoGKPath=/output/runtime-bin/PicoGK.dll \
  -p:BaseIntermediateOutputPath=/output/probe-obj/ -o /output/probe-bin
dotnet /output/probe-bin/Probe.dll
```

For the initial reference, build `Probe.csproj` in another directory with
`PicoGKPath=/opt/station-demo/bin/PicoGK.dll`. The expected exit code 1
is a failure of the initial profile, not a test to work around.

The [linux-checks.sh](../qwen-picogk-tunnel/linux-checks.sh) script consumes,
read-only, an `/input` with a `manifest.sha256` checked by
`sha256sum --check`, and a new `/output`. Input layout:

```text
inference/                 input.json + inference.json from the accepted Mac Qwen run
source/twins/964-chassis/source/qwen-picogk-tunnel/
                           Program.cs + Tunnel.csproj at commit c751517
legacy/twins/993-carbon-safety-cell/
                           design-space.json and the two historical scripts
                           build_structural_screening.py, verify_calculix.py
linux-checks.sh
manifest.sha256            digests of the eight files above
```

For the corrected rerun, also mount the candidate DLL read-only at
`/opt/station-demo/bin/PicoGK.dll` **in this one container only**. The original
tunnel program keeps all its assertions. The output `legacy` copy is the only
one allowed to receive the new CalculiX results.

## Decisive physical limit

The truss does not include the openings of the new tunnel; its stiffness cannot
be transferred to them. Neither the voxelized geometry nor the truss's equivalent
material is a laminated shell mesh. The dynamic clearances,
the measured interfaces, the laminates, the bonds and reinforcements around the
openings, the cure, the molds and the experimental correlation remain to be
defined before any product structural calculation or any manufacturing.
