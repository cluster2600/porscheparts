# LatticeLibrary ribs and VDB exchange for the cylinder head

The [C# runner](source/bionic/HeadBionicRunner.cs) builds the three volumes
with the ShapeKernel generator of the [architectural study](ORIGINAL_ARCHITECTURE.md),
then adds open external ribs built with LatticeLibrary.
They are candidate reinforcements; their placement does not come from a load
or fatigue calculation. The [report](derived/bionic-report.json) keeps
their independent inspection and the provenance of the native run.

## LatticeLibrary as actually used

`CuboidCell` lays out the BCC cells; `BodyCentreLattice` builds
their diagonals and `ConstantBeamThickness` sets a hypothetical diameter of
3.5 mm. The cells measure 12 × 14 × 14 mm, with no random noise.
The complete cells have their inner face embedded in the two flanks,
then are joined to the body. A first, trimmed grid was rejected
for detached external fragments.
There is no lattice in the coolant and no removal of the load-bearing core.
The [references file](source/bionic/references.json) records the
assumptions and the digests of the installed Apache-2.0 sources.

This change adds material. Stiffness, stresses, fatigue, manufacturing
access and thermal interactions must be measured before a reinforcement is
retained. An organic-looking render does not validate these criteria.

## OpenVDB fields actually exchanged

The local file `work/962-head/bionic-native-002/head-fields.vdb` contains:

| Name | Type | Interpretation |
| --- | --- | --- |
| `metal_domain` | Voxels | Body with the candidate ribs |
| `coolant_domain` | Voxels | Conformal water jacket |
| `dry_domain` | Voxels | Dry reservations, including ports, guides and pockets |
| `coolant_native_signed_distance` | ScalarField | Native PicoGK geometric distance |
| `coolant_native_gradient` | VectorField | Native PicoGK geometric gradient |

The fields are read back **by name**: the order of VDB grids is not guaranteed.
The three domains pass `bIsEqual`. Traversing every active value
compares the saved and reloaded scalars and vectors exactly,
in both directions so that added values are also detected. The counts
and the VDB SHA-256 are kept in the report. This derived file stays
local; the code is the editable, shareable source.

No temperature, pressure, coolant velocity or stress is calculated.
The scalar field keeps native grid units. In the inspected API,
`ScalarField.fSignedDistance` multiplies its value by `voxel_mm` to obtain
millimeters; a solver working in meters still needs a division by 1,000.
The gradient keeps its native convention and does not represent a velocity. A successful VDB exchange
does not prove a successful cooling simulation.

## Reproduction

The libraries are those of the recorded references. Build:

```sh
dotnet build twins/962-cylinder-head-f0/source/bionic/Engine.csproj \
  -p:PicoGKBinaryRoot=/path/to/verified-PicoGK-runtime \
  -p:ShapeKernelRoot=/path/to/LEAP71_ShapeKernel \
  -p:LatticeLibraryRoot=/path/to/LEAP71_LatticeLibrary \
  -o work/962-head/bionic-bin
```

Place the verified native dependencies next to the binary and run the
runner **under the shared lock** of
[run_part.py](../../parts/picogk-catalog/tools/run_part.py). It takes the
`source/architecture/` folder and a new output folder. The inspection uses the
verified passage meshes from the previous step:

```sh
python twins/962-cylinder-head-f0/source/bionic/inspect_and_render.py \
  work/962-head/bionic-native-002 work/962-head/bionic-bin \
  /path/to/LEAP71_LatticeLibrary \
  work/962-head/architecture-final-inspected \
  work/962-head/bionic-inspected-new
```

The [interface contracts](interface-contract.json) and manufacturing
authorizations are unchanged. This step completes a software and
geometric study, without qualifying a cylinder head for the 1,000 hp engine kit.
