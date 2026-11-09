"""Analytic harmonic field on four quadrilaterals, including an interior DOF."""
import os
os.environ['JAX_PLATFORMS'] = 'cpu'
import importlib.metadata as metadata
import json
import jax
import jax.numpy as jnp
import numpy as np
from petsc4py import PETSc
from jax_fem.generate_mesh import Mesh
from jax_fem.problem import Problem
from jax_fem.solver import solver

jax.config.update('jax_enable_x64', True)

class Laplace(Problem):
    def get_tensor_map(self):
        return lambda gradient: gradient

points = np.array([[x, y] for y in [0., .5, 1.] for x in [0., .5, 1.]])
cells = np.array([[0,1,4,3],[1,2,5,4],[3,4,7,6],[4,5,8,7]], dtype=np.int32)
boundary = lambda p: jnp.any(jnp.isclose(p, 0.) | jnp.isclose(p, 1.))
exact = lambda p: p[0] + 2 * p[1]
problem = Laplace(mesh=Mesh(points,cells,ele_type='QUAD4'), vec=1, dim=2,
                  ele_type='QUAD4', dirichlet_bc_info=[[boundary],[0],[exact]])
solution = solver(problem, solver_options={'newton':{
    'tol':1e-10, 'rel_tol':1e-10,
    'linear':{'petsc_solver':{'ksp_type':'preonly','pc_type':'lu'}}}})[0]
expected = points[:,0] + 2 * points[:,1]
np.testing.assert_allclose(np.asarray(solution).ravel(), expected, rtol=0, atol=1e-8)
assert abs(float(jax.grad(lambda x: x*x)(3.)) - 6.) < 1e-12
print(json.dumps({'status':'JAX_FEM_PETSC_ANALYTIC_LAPLACE_PASS',
                  'maximum_absolute_error':float(np.max(np.abs(np.asarray(solution).ravel()-expected))),
                  'petsc_version':PETSc.Sys.getVersion(),
                  'versions':{n:metadata.version(n) for n in ['jax','jax-fem','fenics-basix','petsc4py']},
                  'gpu_tested':False,'physical_qualification':False}))
