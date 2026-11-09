# JAX-FEM native runtime

This additive runtime supports stack issues #404–#407. It retains the prepared
JAX CUDA 12 dependency lock, with native PETSc 3.26.1 and petsc4py 3.26.1 built
from SHA-256-pinned source archives. The successful build uses native Linux
AMD64. CUDA dependencies are installed, but GPU execution is not tested.

The first build compiled PETSc but failed to install it because `patchelf` was
missing. After adding that package, PETSc and petsc4py compiled and `pip check`
passed. The smoke then failed on Gmsh's missing `libXrender.so.1`. An `ldd`
diagnostic identified six missing native libraries; the final recipe installs
their Ubuntu packages. Separate install layers preserve the large cached
dependency and compiler layers on the capacity-constrained local builder.
The analytic smoke and hash-pinned Python requirements are unchanged.

From the repository root, on native Linux AMD64:

```sh
docker build --platform linux/amd64 -f containers/stack-20261105/jax-fem.Dockerfile -t porscheparts/jax-fem:stack-20261105 .
docker run --rm --network none --cpus 2 --memory 4g porscheparts/jax-fem:stack-20261105
```

The offline smoke solves a Laplace problem on four quadrilaterals with nine
nodes, including one unconstrained interior degree of freedom. The independent
analytic reference is `u = x + 2*y`, with maximum absolute error required below
`1e-8`. The native run reports zero error. A separate automatic-differentiation
control checks that the derivative of `x*x` at 3 is 6. These are synthetic
software controls, not validation of any catalogue geometry or physical part.

`jax-native-validation.json` records the image ID, source hashes, bounded smoke
limits, actual report and retained receipt hashes. A local image ID is not a
published registry digest. The full logs and installed package list remain in
the private `stack-followup-20261107/receipts/jax-fem.iGxdXZ` artifact directory;
three earlier failed attempts are retained there under their recorded IDs.
No historical recipe, lock, evidence or training corpus is modified. No model
training, GPU test, registry publication or manufacturing qualification occurs.
