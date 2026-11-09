# Qualified Linux PicoGK runner

Issue [#560](https://github.com/cluster2600/porscheparts/issues/560), phase
`picogk`. Read the [head instructions](../../AGENTS.md),
[workflow](../../WORKFLOW.md) and [phase contract](../../workflow-contract.json).

The separate [Linux project](../flow4l/Engine.Linux.csproj) compiles the unchanged
head sources against .NET 10. The historical .NET 9 project and macOS driver
remain unchanged. An initial command-line framework override still restored
.NET 9 reference packs and failed offline; an explicit Linux project restored
and compiled offline in the existing Linux image.

[run_native.py](run_native.py) checks the native ELF architecture, records the
executable, assembly and native-library hashes, and uses the same
`picogk-catalog.lock` name and exclusive-create protocol as the catalogue runner.
It waits at most 30 seconds for that lock and never steals an old lock. Native
execution has a positive limit of at most 600 seconds (120 by default). The whole
process group is killed on timeout; surviving children after a successful parent
also make the run fail. A fresh output directory retains logs and the receipt
on execution failure. Existing outputs are never replaced.

## Native result

[The qualification receipt](qualification-20261107.json) records the actual
Linux x86_64 run in local image
`sha256:fe3603e1a305fc388c55c03efc33a695619290a567cf25e4a789df66ec4ea641`.
This image is retained on the local builder, not published to a registry.
The run used .NET SDK 10.0.403, PicoGK 26.2, the pinned ShapeKernel and
LatticeLibrary revisions, two CPU cores, 4 GiB memory and no network.
The host shared lock was held around the owned container as well as inside it;
container absence and release of the host lock were checked afterward.

The qualification entry point uses three synthetic 10 × 20 × 30 mm boxes and
one body-centred lattice cell. It does not invoke the head generator. Named
metal, coolant, dry and lattice voxel grids survive a VDB round trip.
The independent [Trimesh check](check_witness.py) measures the exported STL
coordinates and volumes, rather than accepting dimensions from the native
report. All three boxes measured 6000.00001755 mm³, with maximum bound error
8.94e-8 mm. All four meshes were watertight. The acceptance limits are 0.5 mm
for bounds and 10% for box volume; these are software witness limits.

Seven process/lock boundary tests also passed inside the native Linux image.
The source context, actual argv, library identities, output hashes, independent
measurements and retained logs are bound by the receipt. The original failed
restore and successful compile probe remain in the private work receipts.

## Reproduction

Use the qualified image or independently requalify a Linux installation with
the exact revisions in the receipt. The retained context maps the current
repository source to `/context`, output to `/output`, PicoGK binaries to `/app`,
ShapeKernel to `/upstream/LEAP71_ShapeKernel`, and the pinned LatticeLibrary
checkout to `/context/libraries/LEAP71_LatticeLibrary`.

Inside that environment, compile the qualification entry point to a fresh
directory:

```sh
dotnet build /context/twins/962-cylinder-head-f0/source/flow4l/Engine.Linux.csproj \
  -c Release -p:Qualification=true -p:PicoGKBinaryRoot=/app \
  -p:ShapeKernelRoot=/upstream/LEAP71_ShapeKernel \
  -p:LatticeLibraryRoot=/context/libraries/LEAP71_LatticeLibrary \
  -p:BaseIntermediateOutputPath=/output/obj/ -o /output/bin
python3 /context/twins/962-cylinder-head-f0/source/linux_runtime/run_native.py \
  /usr/share/dotnet/dotnet /output/bin/Engine.Linux.dll \
  /app/picogk.26.2.so /output/qualification --seconds 120
```

Run `check_witness.py OUTPUT/qualification/native` separately in the retained
Trimesh environment and retain its JSON output. A wrapper receipt with status
`executed` alone does not constitute independent acceptance.

For a container run, take the host's shared lock before starting the container;
an isolated container's `/tmp` lock cannot coordinate host processes. Use an
owned container ID, a bounded outer controller, an init process for reaping,
no network and explicit CPU/memory limits. Remove that owned container and
confirm its absence before releasing the host lock. The native wrapper itself
can also run directly on a separately qualified Linux installation.

For a separately admitted study, compile without `Qualification=true` into a
different directory and supply `--inputs` containing `solid.json`,
`coolant.json` and `dry-passages.json`. First bind its actual inputs/runtime in
the nineteen-phase ledger and pass `workflow_plan.py --check-plan PLAN
--require-ready picogk`. No study execution was performed for this qualification.

## Engineering status

Only the `picogk` **runtime** is software-qualified. All nineteen engineering
phase states remain `blocked`, as recorded in the receipt. The private complete
ledger includes the runtime receipt and passed the workflow checker; its SHA-256
is `70955b81d277b0da6a83e523749630edc0da641ed59d07bbd42682ffb0af98a5`.
Provenance acceptance, measured donor interfaces and concrete input bindings
still prevent preparation or execution of the engineering phase.

The witness does not validate head geometry, scalar/vector VDB values, GPU
behavior, loads, flow, strength, manufacturing or physical interfaces. Fasteners
were not applicable to these synthetic boxes; functional fasteners still need
measured attachments. No engineering phase is promoted by this receipt.
