# Print distortion: carrier calculation contract

## Check executed on 16 October 2026

The existing patched binary and its manifest were verified on Kali1:
`e7637a1a3729f82c0b11a9a1864fd96b7fbdee9408ede0aad5b59e573699b959`
and `642a7f8c7928a2bf8171162f4928a02c093fc0677956c3c7023d37a12a1b128f`.
The `Geometry.cc` code is identical to revision
`3990489a10902912889617856f6e2e097d52a412`, SHA-256
`d58cab9a1220a61324dff91aabdc639982238cbd62642b0cb5b9e72a23101b47`.

A small native call to `Geometry::is_within_stl`, linked against the already
compiled object, was configured and then failed to compile in 2.75 s: this method
does not exist in this runtime. The installed package is **ArborX 1.5**; the code
requires `ARBORX_VERSION_MAJOR >= 2` for STL filtering. The compiled object
contains the STL readers but no `is_within_stl` symbol.

The sources of the check are `adamantine_occupation.cc` and
`occupation-CMakeLists.txt`. The inputs, logs and digests are kept
in `work/carrier-process-20261016/adamantine-occupation-001/`.
The geometric input of the check is the V6f Gmsh006 remeshing, SHA-256
`8fe38c5069bc20831257dced425d91770ad76cfd4109276998a21cf60b7ecfb2`,
flat, rotated 45° in plane, with 10 mm under the part. It is the
reference geometric witness, not the new mechanical revision.
**No carrier occupation or distortion was calculated by this check;
zero thermal steps and zero mechanical solves.**

## Concrete limits of the STL route

The [Geometry constructor](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/Geometry.cc)
generates a box of hexahedra around the STL. With ArborX 2, the predicate rejects
every cell cutting the surface and then tests the cells entirely
inside. It is an inner approximation; thin walls
shrink or disappear if the mesh is coarse. With ArborX 1.5,
the [activation selection](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/material_deposition.cc)
branch does not filter the STL shape. Reading an STL without error therefore does not prove that the
activated material represents the carrier.

The other input is `geometry.import_mesh true`, `mesh_format gmsh`,
`mesh_file ...`, `units.mesh millimeter`. The engine uses hexahedral `FE_Q`
elements: CalculiX's tetrahedral C3D10 is not interchangeable.
A conforming HEX import, or a HEX whose occupation has already been audited, avoids the
missing STL filtering, without by itself resolving the other limits of the model.

The [native refinement](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/application/adamantine.hh)
refines near the source trajectory up to `n_refinements`;
`coarsen_after_beam` and `time_steps_between_refinement` drive the transfer.
It guarantees neither three elements across a 1.5 mm wall nor the
preservation of its geometry. Activation selects the cells intersecting
a deposition box: a tall cell can be activated as soon as the first
60 µm layer touches it.

As a budget, for the witness alone of 268,852 mm³ and its
451.134 × 451.134 × 52 mm box, the numbers below are `volume/h³`
**estimates** and structured-box counts, not executed meshes.
They exclude the build plate and the supports.

| Isotropic size h | Estimated material cells | Box cells |
| --- | ---: | ---: |
| 0.5 mm | 2,150,816 | 84,802,536 |
| 0.25 mm | 17,206,532 | 677,669,200 |
| 0.06 mm | 1,244,685,456 | 49,016,157,987 |

## Mechanical response and sequence to prepare

The installed profile limits properties to constants, a single material,
CPU memory and 3D. The [mechanical solver](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/MechanicalPhysics.cc)
solves the elastic displacement by conjugate gradient, then applies a J2 radial
return to the stresses. The [right-hand side](https://github.com/adamantine-sim/adamantine/blob/3990489a10902912889617856f6e2e097d52a412/source/MechanicalOperator.cc)
contains the thermal expansions and the forces; the plastic return does not
re-equilibrate this displacement through a global iteration. This code must therefore
not be equated with a converged global elastoplastic solution of
residual shrinkage. Nor does the examined contract provide a ready-to-use
plate/support release step.

The shortest route for the pilot remains **existing CalculiX**, with the STEP and
the new mesh, deposition groups explicitly distinguished from the 60 µm
layers, a bounded inherent strain and the release of stresses
in the same calculation state. A thermal then elastoplastic route additionally requires
the thermal fields and the temperature-dependent Ti64 law. The publication
[OpenAM-SimCCX](https://doi.org/10.3390/ma18214990) describes such a
CalculiX chain; its data are in the author collection
[10.6084/m9.figshare.c.8086513](https://doi.org/10.6084/m9.figshare.c.8086513).
It is neither a newly installed runtime nor a result for this carrier.

Before a complete prediction, freeze then verify:

1. Geometry of the material and of the volumetric supports, build plate and interfaces. The
   open PySLM surfaces do not directly give their mass or their
   volumetric conductance.
2. At least three elements across the 1.5 mm walls as a starting
   point, then independent refinement; this number alone is not a convergence
   criterion. Also check volume, connectivity, bores and supports.
3. Vertical bounds of each element and activation layer/group, with
   published activation error. A comparison of groups on an identical mesh
   is not spatial refinement.
4. Cooling, then support removal and plate release while
   preserving the mechanical state. Measure displacements after registration on
   the same supports and the same procedure as the reference calculation.
5. Spatial variation and group/time-step variation kept separate,
   with the protocol's convergence threshold frozen before the calculations. Keep
   the existing 10 % rejection rule for activation sensitivity;
   no value from a non-converged case becomes an accepted distortion.

This study launched neither a new heavy installation nor an insufficiently resolved
global thermomechanical calculation. Adding ArborX 2 alone would not be enough
to turn the current profile into a complete predictor of residual shrinkage.
