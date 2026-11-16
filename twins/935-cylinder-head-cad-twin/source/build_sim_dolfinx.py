#!/usr/bin/env python3
"""The build screen's mechanical model in DOLFINx: a second solver, in parallel, for the same case.

build_sim.py solves the mechanics in CalculiX on one thread with a direct solver, which keeps
the 2 mm level out of reach of this host. This script states the same model in DOLFINx (PETSc,
MPI) so that it can be solved on several cores, with a choice of linear solver:

  elements    8-node hexahedra, 2 x 2 x 2 Gauss points, small strain (CalculiX C3D8);
  birth       a cell is added strain free: the strain it has when it is added, and the mean
              temperature of its nodes at that moment, are its reference from then on;
  material    isotropic elasticity with a modulus by temperature, von Mises plasticity with a
              yield stress by temperature and linear isotropic hardening, radial return;
  temperature the mean of a cell's nodal temperatures, as CalculiX uses for its linear elements;
  release     plate and supports are removed and the part is held at three nodes.

The temperatures are those of build_sim.py's thermal run (thermal-end-of-lump.npy): this script
has no thermal model. It reads a run folder prepared by build_sim.py.

Linear solvers: mumps (LU at every Newton iteration), blr (a compressed Cholesky factorisation
per increment, kept as the preconditioner of conjugate gradients; the one that fits the 2 mm
level in memory) and gamg (conjugate gradients on algebraic multigrid; little memory, slow here
because the plastic tangent is far softer along the flow direction than across it).

Usage (witness and mechanics inside the DOLFINx image, see run_twin.sh; compare and record
need NumPy only):
  build_sim_dolfinx.py witness OUT.json
  build_sim_dolfinx.py mechanics RUN_DIR OUT_DIR [--solver mumps|blr|gamg] [--increments N]
  build_sim_dolfinx.py compare CCX_RUN_DIR DOLFINX_DIR ACCEPTANCE.json OUT.json
  build_sim_dolfinx.py record PRIVATE_DIR CCX_RECORD.json ACCEPTANCE.json OUT.json

This is a screen under declared hypotheses. It qualifies no process, support scheme,
orientation, material or part.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

K0 = 273.15
HEX = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
TO_DOLFINX = [0, 1, 3, 2, 4, 5, 7, 6]            # CalculiX C3D8 corner order to DOLFINx's tensor order
NEVER_YIELDS = 1.0e30
IMAGE = "dolfinx/dolfinx@sha256:58b27e84a2f26b98ce2d9ccc537b0ee6a59e2fcfdf386626d5ed9ddf43425ece"      # v0.11.0.post0, amd64
REFERENCE_LEVEL = "c4-l8"      # the level both solvers ran
KEPT = []                      # solids of earlier witnesses, kept until exit so that Python's collector frees no parallel
                               # PETSc object at a different moment on each process (a precaution, not a diagnosed fault)
BLR_MAX_ITERATIONS = 60        # of the conjugate-gradient loop on a kept factorisation, before it is made again
BLR_REFACTOR_ABOVE = 25        # iterations of one solve above which the next solve starts from a new factorisation


class Solid:
    """Cells that can be added strain free and removed, under nodal temperatures and fixed dofs."""

    def __init__(self, xyz, conn, cell_material, materials, solver="mumps", log=None):
        """materials: {id: {"E": [[T_K, MPa], ...], "nu", "alpha", "yield": [[T_K, MPa], ...] or None, "hardening"}}."""

        from mpi4py import MPI
        from petsc4py import PETSc
        import basix
        import basix.ufl
        import ufl
        from dolfinx import fem, mesh
        import dolfinx.fem.petsc as fpetsc

        self.MPI, self.PETSc, self.fem, self.fpetsc = MPI, PETSc, fem, fpetsc
        self.comm = MPI.COMM_WORLD
        self.rank = self.comm.rank
        self.log = log or (lambda *a: None)
        self.n_nodes, self.n_cells = len(xyz), len(conn)
        self.conn_in = np.asarray(conn, dtype=np.int64)
        self.cell_material_in = np.asarray(cell_material)
        self.materials = materials

        element = basix.ufl.element("Lagrange", "hexahedron", 1, shape=(3,))
        cells = self.conn_in[:, TO_DOLFINX] if self.rank == 0 else np.zeros((0, 8), dtype=np.int64)
        points = np.asarray(xyz, dtype=np.float64) if self.rank == 0 else np.zeros((0, 3))
        self.mesh = msh = mesh.create_mesh(self.comm, cells, element, points)
        tdim = msh.topology.dim
        cmap = msh.topology.index_map(tdim)
        self.cells_local = cmap.size_local + cmap.num_ghosts
        self.cells_owned = cmap.size_local
        self.cell_in = np.asarray(msh.topology.original_cell_index[:self.cells_local], dtype=np.int64)

        self.V = V = fem.functionspace(msh, ("Lagrange", 1, (3,)))
        self.dofs_local = V.dofmap.index_map.size_local + V.dofmap.index_map.num_ghosts
        self.dofs_owned = V.dofmap.index_map.size_local
        self.cell_dofs = np.asarray(V.dofmap.list[:self.cells_local])
        node_in = np.full(self.dofs_local, -1, dtype=np.int64)
        gmap = np.asarray(msh.geometry.input_global_indices)
        node_in[self.cell_dofs.ravel()] = gmap[np.asarray(msh.geometry.dofmaps[0][:self.cells_local]).ravel()]
        assert (node_in >= 0).all()
        self.node_in = node_in                                   # local block dof -> node of the input
        # the same local corner order in both maps: the cell's nodes of the input, in DOLFINx's order
        assert np.array_equal(np.sort(node_in[self.cell_dofs], axis=1), np.sort(self.conn_in[self.cell_in], axis=1))

        dg0 = fem.functionspace(msh, ("DG", 0))
        q_scalar = fem.functionspace(msh, basix.ufl.quadrature_element("hexahedron", (), "default", 2))
        q_tensor = fem.functionspace(msh, basix.ufl.quadrature_element("hexahedron", (3, 3), "default", 2))
        self.q_points, _ = basix.make_quadrature(basix.CellType.hexahedron, 2)
        assert len(self.q_points) == 8
        f = fem.Function
        self.u, self.du = f(V), f(V)
        self.act, self.E, self.nu, self.sy, self.H, self.eth = (f(dg0) for _ in range(6))
        self.p, self.eb, self.ep = f(q_scalar), f(q_tensor), f(q_tensor)
        # a cell's dofs in a DG0 or quadrature space are the cell's own, in cell order
        assert np.array_equal(np.asarray(dg0.dofmap.list[:self.cells_local]).ravel(), np.arange(self.cells_local))
        assert np.array_equal(np.asarray(q_scalar.dofmap.list[:self.cells_local]).ravel(), np.arange(8 * self.cells_local))

        mat = self.cell_material_in[self.cell_in]
        self.mat_local = mat
        self.nu.x.array[:self.cells_local] = [materials[int(k)]["nu"] for k in mat]
        self.H.x.array[:self.cells_local] = [materials[int(k)]["hardening"] for k in mat]
        self.alpha = np.array([materials[int(k)]["alpha"] for k in mat])
        self.t_birth = np.zeros(self.cells_local)
        self.active = np.zeros(self.n_cells, dtype=bool)         # by cell of the input, the same on every rank
        self.T = np.zeros(self.n_nodes)                          # by node of the input, the same on every rank

        u, v, w = self.u, ufl.TestFunction(V), ufl.TrialFunction(V)
        eye = ufl.Identity(3)
        strain = ufl.sym(ufl.grad(u))
        elastic_trial = strain - self.eb - self.ep - self.eth * eye
        shear = self.E / (2.0 * (1.0 + self.nu))
        bulk = self.E / (3.0 * (1.0 - 2.0 * self.nu))
        s_trial = 2.0 * shear * ufl.dev(elastic_trial)
        q_trial = ufl.sqrt(1.5 * ufl.inner(s_trial, s_trial) + 1.0e-16)
        dp = ufl.max_value(q_trial - (self.sy + self.H * self.p), 0.0) / (3.0 * shear + self.H)
        stress = bulk * ufl.tr(elastic_trial) * eye + s_trial * (1.0 - 3.0 * shear * dp / q_trial)
        dx = ufl.Measure("dx", domain=msh, metadata={"quadrature_degree": 2, "quadrature_scheme": "default"})
        residual = self.act * ufl.inner(stress, ufl.sym(ufl.grad(v))) * dx
        self.F = fem.form(residual)
        self.J = fem.form(ufl.derivative(residual, u, w))
        self.x_strain = fem.Expression(strain, self.q_points)
        self.x_stress = fem.Expression(stress, self.q_points)
        self.x_dp = fem.Expression(dp, self.q_points)
        self.x_flow = fem.Expression(1.5 * dp * s_trial / q_trial, self.q_points)
        self.all_cells = np.arange(self.cells_local, dtype=np.int32)

        self.A = fpetsc.create_matrix(self.J)
        self.b = fpetsc.create_vector(V)
        self.ksp = ksp = PETSc.KSP().create(self.comm)
        ksp.setOperators(self.A)
        self.solver = solver
        if solver == "mumps":
            ksp.setType("preonly")
            ksp.getPC().setType("lu")
            ksp.getPC().setFactorSolverType("mumps")
        elif solver == "blr":
            # one compressed (block low-rank) Cholesky factorisation per increment, kept as the preconditioner of a
            # conjugate-gradient loop while the tangent changes; made again when the loop needs too many iterations
            ksp.setType("cg")
            ksp.setTolerances(rtol=1.0e-10, max_it=BLR_MAX_ITERATIONS)
            ksp.getPC().setType("cholesky")
            ksp.getPC().setFactorSolverType("mumps")
            opts = PETSc.Options()
            opts["mat_mumps_icntl_35"] = 2
            opts["mat_mumps_cntl_7"] = 1.0e-6
            ksp.setFromOptions()
        else:
            assert solver == "gamg", solver
            ksp.setType("cg")
            ksp.setTolerances(rtol=1.0e-9, max_it=4000)
            ksp.getPC().setType("gamg")
            opts = PETSc.Options()
            opts["pc_gamg_threshold"] = 0.02
            opts["mg_levels_ksp_type"] = "chebyshev"
            opts["mg_levels_pc_type"] = "jacobi"
            ksp.setFromOptions()
            x = V.tabulate_dof_coordinates()[:self.dofs_local]
            modes = []
            for k in range(6):
                vec = self.A.createVecLeft()
                a = vec.getArray()
                block = np.zeros((self.dofs_owned, 3))
                xo = x[:self.dofs_owned]
                if k < 3:
                    block[:, k] = 1.0
                else:
                    i, j = [(1, 2), (2, 0), (0, 1)][k - 3]
                    block[:, i], block[:, j] = -xo[:, j], xo[:, i]
                a[:] = block.ravel()
                vec.assemble()
                modes.append(vec)
            self.near_null = PETSc.NullSpace().create(vectors=self._orthonormal(modes), comm=self.comm)
            self.A.setNearNullSpace(self.near_null)
        self.fixed = {}                                           # (node of the input, component) held where it is
        self.bcs = []
        self.force_scale = 0.0
        self.refactor = True
        self.counts = {"newton_iterations": 0, "linear_iterations": 0, "increments": 0, "line_searches": 0, "factorisations": 0}

    @staticmethod
    def _orthonormal(vectors):
        for i, v in enumerate(vectors):
            for w in vectors[:i]:
                v.axpy(-v.dot(w), w)
            v.normalize()
        return vectors

    # ------------------------------------------------------------------ state

    def cell_temperature(self):
        return self.T[self.conn_in[self.cell_in]].mean(axis=1)

    def refresh_material(self):
        """Modulus, yield stress and thermal strain of every local cell at the current temperatures."""

        t = self.cell_temperature()
        e, sy = np.zeros(self.cells_local), np.zeros(self.cells_local)
        for key, m in self.materials.items():
            sel = self.mat_local == key
            table = np.array(m["E"])
            e[sel] = np.interp(t[sel], table[:, 0], table[:, 1])
            if m["yield"] is None:
                sy[sel] = NEVER_YIELDS
            else:
                table = np.array(m["yield"])
                sy[sel] = np.interp(t[sel], table[:, 0], table[:, 1])
        self.E.x.array[:self.cells_local] = e
        self.sy.x.array[:self.cells_local] = sy
        self.eth.x.array[:self.cells_local] = self.alpha * (t - self.t_birth)

    def add(self, cells_in):
        """Add cells strain free at the current displacements and temperatures."""

        new = np.zeros(self.n_cells, dtype=bool)
        new[cells_in] = True
        assert not (new & self.active).any()
        self.active |= new
        local = np.flatnonzero(new[self.cell_in]).astype(np.int32)
        if len(local):
            self.eb.x.array.reshape(self.cells_local, 8, 9)[local] = self.x_strain.eval(self.mesh, local).reshape(len(local), 8, 9)
            self.ep.x.array.reshape(self.cells_local, 8, 9)[local] = 0.0
            self.p.x.array.reshape(self.cells_local, 8)[local] = 0.0
            self.t_birth[local] = self.cell_temperature()[local]
        self._after_change()

    def remove(self, cells_in):
        gone = np.zeros(self.n_cells, dtype=bool)
        gone[cells_in] = True
        self.active &= ~gone
        self._after_change()

    def hold(self, node, component):
        self.fixed[(int(node), int(component))] = True
        self._constraints()

    def _after_change(self):
        self.act.x.array[:self.cells_local] = self.active[self.cell_in]
        self._constraints()

    def _constraints(self):
        """Dofs of nodes with no active cell, and the dofs held by name, keep the value they have."""

        live = np.zeros(self.n_nodes, dtype=bool)
        live[self.conn_in[self.active].ravel()] = True
        held = np.zeros((self.n_nodes, 3), dtype=bool)
        held[~live] = True
        for node, component in self.fixed:
            held[node, component] = True
        mask = held[self.node_in]                                 # local block dof by component
        self.bcs = []
        for c in range(3):
            dofs = (3 * np.flatnonzero(mask[:, c]) + c).astype(np.int32)
            self.bcs.append(self.fem.dirichletbc(self.PETSc.ScalarType(0.0), dofs, self.V.sub(c)))

    # ------------------------------------------------------------------ solve

    def _residual(self):
        b, PETSc = self.b, self.PETSc
        with b.localForm() as loc:
            loc.set(0.0)
        self.fpetsc.assemble_vector(b, self.F)
        b.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
        self.fpetsc.set_bc(b, self.bcs)
        return b.norm()

    def equilibrium(self, label=""):
        """Newton iterations on the displacement at the current temperatures and state; then the state is advanced."""

        PETSc = self.PETSc
        self.refresh_material()
        self.refactor = True
        r0 = self._residual()
        self.force_scale = max(self.force_scale, r0)
        norm, it = r0, 0
        while norm > 1.0e-8 * self.force_scale and it < 40:
            self.A.zeroEntries()
            self.fpetsc.assemble_matrix(self.A, self.J, bcs=self.bcs)
            self.A.assemble()
            self.b.scale(-1.0)
            if self.solver == "blr":
                self.A.setOption(PETSc.Mat.Option.SPD, True)              # the flag does not outlive an assembly
                self.ksp.getPC().setReusePreconditioner(not self.refactor)
                self.counts["factorisations"] += int(self.refactor)
                self.ksp.solve(self.b, self.du.x.petsc_vec)
                self.counts["linear_iterations"] += self.ksp.getIterationNumber()
                if self.ksp.getConvergedReason() <= 0 and not self.refactor:      # the kept factorisation is too old
                    self.ksp.getPC().setReusePreconditioner(False)
                    self.counts["factorisations"] += 1
                    self.ksp.solve(self.b, self.du.x.petsc_vec)
                    self.counts["linear_iterations"] += self.ksp.getIterationNumber()
                self.refactor = self.ksp.getIterationNumber() > BLR_REFACTOR_ABOVE
            else:
                self.counts["factorisations"] += int(self.solver == "mumps")
                self.ksp.solve(self.b, self.du.x.petsc_vec)
                self.counts["linear_iterations"] += self.ksp.getIterationNumber()
            assert self.ksp.getConvergedReason() > 0, f"linear solver: reason {self.ksp.getConvergedReason()} ({label})"
            self.du.x.scatter_forward()
            step, before = 1.0, self.u.x.array.copy()
            while True:                                           # halve the step while the residual grows
                self.u.x.array[:] = before + step * self.du.x.array
                trial = self._residual()
                if trial < norm or step < 1.0 / 16.0 or it == 0:
                    break
                step *= 0.5
                self.counts["line_searches"] += 1
            norm, it = trial, it + 1
        assert norm <= 1.0e-8 * self.force_scale, f"Newton did not converge: {norm:.3e} against {self.force_scale:.3e} ({label})"
        self.counts["newton_iterations"] += it
        self.counts["increments"] += 1
        # advance the plastic state
        flow = self.x_flow.eval(self.mesh, self.all_cells).reshape(self.cells_local, 8, 9)
        dp = self.x_dp.eval(self.mesh, self.all_cells).reshape(self.cells_local, 8)
        on = self.active[self.cell_in]
        self.ep.x.array.reshape(self.cells_local, 8, 9)[on] += flow[on]
        self.p.x.array.reshape(self.cells_local, 8)[on] += dp[on]
        self.log(f"{label}: residual {r0:.3e} -> {norm:.3e} in {it} iterations")
        return it

    def ramp(self, nodes, targets, increments, label=""):
        """Bring the given nodes to their target temperatures in equal increments."""

        nodes = np.asarray(nodes)
        start = self.T[nodes].copy()
        for k in range(1, increments + 1):
            self.T[nodes] = start + (np.asarray(targets) - start) * k / increments
            self.equilibrium(f"{label} {k}/{increments}")

    # ------------------------------------------------------------------ read

    def displacement(self):
        """Displacement by node of the input, gathered on rank 0 (None elsewhere)."""

        own = slice(0, self.dofs_owned)
        parts = self.comm.gather((self.node_in[own], self.u.x.array.reshape(-1, 3)[own].copy()), root=0)
        if self.rank:
            return None
        out = np.zeros((self.n_nodes, 3))
        for nodes, values in parts:
            out[nodes] = values
        return out

    def stress_and_plastic_strain(self):
        """By cell of the input, at its eight Gauss points: stress (xx, yy, zz, xy, xz, yz) and equivalent plastic strain."""

        self.refresh_material()
        own = np.arange(self.cells_owned, dtype=np.int32)
        s = self.x_stress.eval(self.mesh, own).reshape(len(own), 8, 3, 3)
        six = np.stack([s[..., 0, 0], s[..., 1, 1], s[..., 2, 2], s[..., 0, 1], s[..., 0, 2], s[..., 1, 2]], axis=-1)
        p = self.p.x.array.reshape(self.cells_local, 8)[:self.cells_owned]
        parts = self.comm.gather((self.cell_in[:self.cells_owned], six, p.copy()), root=0)
        if self.rank:
            return None, None
        stress, peeq = np.zeros((self.n_cells, 8, 6)), np.zeros((self.n_cells, 8))
        for cells, a, b in parts:
            stress[cells], peeq[cells] = a, b
        return stress, peeq


def von_mises(s):
    return np.sqrt(0.5 * ((s[..., 0] - s[..., 1]) ** 2 + (s[..., 1] - s[..., 2]) ** 2 + (s[..., 2] - s[..., 0]) ** 2)
                   + 3.0 * (s[..., 3] ** 2 + s[..., 4] ** 2 + s[..., 5] ** 2))


def remove_rigid(xyz, u):
    """Least-squares removal of a small rigid motion (as in build_sim.py)."""

    r = xyz - xyz.mean(axis=0)
    basis = np.zeros((len(r), 3, 6))
    basis[:, :, :3] = np.eye(3)
    basis[:, 0, 4], basis[:, 0, 5] = r[:, 2], -r[:, 1]
    basis[:, 1, 3], basis[:, 1, 5] = -r[:, 2], r[:, 0]
    basis[:, 2, 3], basis[:, 2, 4] = r[:, 1], -r[:, 0]
    flat = basis.reshape(-1, 6)
    return u - (flat @ np.linalg.lstsq(flat, u.ravel(), rcond=None)[0]).reshape(-1, 3)


# --------------------------------------------------------------------------
# witness: the bar of build_sim.py


def box(nx, ny, nz, h):
    nid = lambda i, j, k: i + (nx + 1) * (j + (ny + 1) * k)
    xyz = np.array([[i * h, j * h, k * h] for k in range(nz + 1) for j in range(ny + 1) for i in range(nx + 1)], dtype=float)
    conn, row = [], []
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                conn.append([nid(i + a, j + b, k + c) for a, b, c in HEX])
                row.append(k)
    return xyz, np.array(conn), np.array(row), nid


def witness_bar(yield_mpa, solver="mumps"):
    """The bar of build_sim.py's witness: held at both ends, the upper half born strain free, then cooled.

    Bar 20 x 4 x 8 mm on 2 mm cells, ends fixed along the bar, Poisson's ratio 0, E = 70 GPa,
    expansion 2.3e-5 /K. Lower half from 500 to 400 K: 161 MPa. The upper half is added strain
    free, its own nodes at 800 K, the interface at 400 K. Everything cools to 300 K. Elastic:
    322 MPa in the lower half, 483 MPa in the row at the interface and 805 MPa in the upper row.
    With a yield of 200 MPa and no hardening: 200 MPa of von Mises stress everywhere.
    """

    xyz, conn, row, nid = box(10, 2, 4, 2.0)
    material = {0: {"E": [[0.0, 70000.0], [2000.0, 70000.0]], "nu": 0.0, "alpha": 2.3e-5,
                    "yield": None if yield_mpa is None else [[0.0, yield_mpa], [2000.0, yield_mpa]], "hardening": 0.0}}
    body = Solid(xyz, conn, np.zeros(len(conn), dtype=int), material, solver)
    old = np.flatnonzero(xyz[:, 2] <= 4.0 + 1e-9)
    new = np.flatnonzero(xyz[:, 2] > 4.0 + 1e-9)
    body.T[old], body.T[new] = 500.0, 800.0
    for i in (0, 10):
        for k in range(5):
            for j in range(3):
                body.fixed[(nid(i, j, k), 0)] = True
    for node, components in ((nid(0, 0, 0), (1, 2)), (nid(10, 0, 0), (2,)), (nid(0, 2, 0), (2,))):
        for c in components:
            body.fixed[(node, c)] = True
    body.add(np.flatnonzero(row < 2))
    steps = []

    def read(label):
        stress, _ = body.stress_and_plastic_strain()
        if body.rank:
            return
        live = body.active
        steps.append({"state": label,
                      "sxx_MPa_by_cell_row": [[round(float(stress[(row == r) & live][..., 0].min()), 2), round(float(stress[(row == r) & live][..., 0].max()), 2)]
                                              if ((row == r) & live).any() else None for r in range(4)],
                      "von_mises_MPa": [round(float(von_mises(stress[live]).min()), 3), round(float(von_mises(stress[live]).max()), 3)]})

    body.ramp(np.arange(len(xyz)), np.full(len(xyz), 400.0), 1, "lower half to 400 K")
    read("lower half at 400 K")
    body.T[new] = 800.0
    body.add(np.flatnonzero(row >= 2))
    body.equilibrium("birth of the upper half")
    read("upper half born")
    body.ramp(np.arange(len(xyz)), np.full(len(xyz), 300.0), 4, "cooling to 300 K")
    read("cooled to 300 K")
    KEPT.append(body)
    return {"steps": steps, "counts": body.counts}


def witness(out) -> None:
    from mpi4py import MPI
    import dolfinx

    want = [322.0, 322.0, 483.0, 805.0]
    by_solver = {}
    for solver in ("mumps", "blr", "gamg"):
        elastic = witness_bar(None, solver)
        plastic = witness_bar(200.0, solver)
        if MPI.COMM_WORLD.rank:
            continue                                               # the fields are gathered on the first process
        birth, last = elastic["steps"][1]["sxx_MPa_by_cell_row"], elastic["steps"][2]["sxx_MPa_by_cell_row"]
        elastic["passed"] = bool(all(abs(v) < 0.01 for v in birth[2] + birth[3]) and all(abs(v - 161.0) < 0.01 for v in birth[0] + birth[1])
                                 and all(abs(lo - w) < 0.05 and abs(hi - w) < 0.05 for (lo, hi), w in zip(last, want)))
        vm = plastic["steps"][-1]["von_mises_MPa"]
        plastic["passed"] = bool(abs(vm[0] - 200.0) < 0.05 and abs(vm[1] - 200.0) < 0.05)
        by_solver[solver] = {"bar_elastic": elastic, "bar_perfectly_plastic": plastic, "passed": bool(elastic["passed"] and plastic["passed"])}
    if MPI.COMM_WORLD.rank:
        return
    record = {"schema": "935-cad-twin-build-sim-dolfinx-witness/2", "date": time.strftime("%Y-%m-%d"),
              "tool": f"DOLFINx {dolfinx.__version__}, {MPI.COMM_WORLD.size} process(es)",
              "acceptance": "the closed-form values and tolerances of params/build-sim-witness.json, set for CalculiX before this tool was tried",
              "bar": witness_bar.__doc__.split("\n")[0],
              "expected_sxx_MPa_by_cell_row_after_cooling": want, "expected_von_mises_MPa_after_cooling_when_perfectly_plastic": 200.0,
              "by_linear_solver": by_solver,
              "passed": bool(all(v["passed"] for v in by_solver.values())),
              "claims": "software witnesses of strain-free birth and perfect plasticity in this DOLFINx model on a bar; "
                        "no process, machine, material or part is qualified"}
    Path(out).write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v["passed"] for k, v in by_solver.items()}))


# --------------------------------------------------------------------------
# mechanics: the head, lump by lump


def mechanics(run_dir, out_dir, *options) -> None:
    from mpi4py import MPI
    import dolfinx

    comm = MPI.COMM_WORLD
    run, out = Path(run_dir), Path(out_dir)
    solver = options[options.index("--solver") + 1] if "--solver" in options else "mumps"
    increments = int(options[options.index("--increments") + 1]) if "--increments" in options else 2
    m = np.load(run / "mesh.npz")
    case = json.loads((run / "case.json").read_text())
    level = (run / "level.txt").read_text().strip()
    lv = case["levels"][level]
    if lv.get("supports") == "designed":
        case["supports"] = {**case["supports"], "solid_fraction": json.loads((run / "prepare.json").read_text())["support_solid_fraction"]}
    mat, f, pl = case["material"], case["supports"]["solid_fraction"], case["plate"]
    t_plate, t_room, t_relax = pl["temperature_K"], case["cooldown"]["room_temperature_K"], mat["stress_free_temperature_K"]
    temps = np.load(run / "thermal-end-of-lump.npy")
    kind, lump, node_lump, xyz, conn = m["kind"], m["lump"], m["node_lump"], m["xyz"], m["conn"]
    lumps = int(lump.max()) + 1
    table = lambda rows, scale: [[t + K0, v * scale] for t, v in rows]
    materials = {
        1: {"E": [[0.0, pl["youngs_modulus_MPa"]], [5000.0, pl["youngs_modulus_MPa"]]], "nu": pl["poisson_ratio"],
            "alpha": pl["thermal_expansion_per_K"], "yield": None, "hardening": 0.0},
        2: {"E": table(mat["youngs_modulus_MPa_by_temperature_C"], 1.0), "nu": mat["poisson_ratio"], "alpha": mat["thermal_expansion_per_K"],
            "yield": table(mat["yield_MPa_by_temperature_C"], 1.0), "hardening": mat["hardening_modulus_MPa"]},
        3: {"E": table(mat["youngs_modulus_MPa_by_temperature_C"], f), "nu": mat["poisson_ratio"], "alpha": mat["thermal_expansion_per_K"],
            "yield": table(mat["yield_MPa_by_temperature_C"], f), "hardening": mat["hardening_modulus_MPa"] * f},
    }
    started = time.time()
    say = (lambda *a: print(f"[{time.time() - started:8.1f} s]", *a, flush=True)) if comm.rank == 0 else None
    body = Solid(xyz, conn, kind, materials, solver, say)
    if comm.rank == 0:
        out.mkdir(parents=True, exist_ok=True)
        say(f"{level}: {len(xyz)} nodes, {len(conn)} cells, {lumps} lumps, {comm.size} process(es), solver {solver}")

    # plate: lower face kept plane, free to shrink in its plane (the same two nodes as build_sim.py)
    bottom = np.flatnonzero(np.isclose(xyz[:, 2], xyz[:, 2].min()))
    a = bottom[np.lexsort((xyz[bottom, 1], xyz[bottom, 0]))[0]]
    b = bottom[np.lexsort((xyz[bottom, 1], -xyz[bottom, 0]))[0]]
    for node in bottom:
        body.fixed[(int(node), 2)] = True
    body.fixed[(int(a), 0)] = body.fixed[(int(a), 1)] = body.fixed[(int(b), 1)] = True
    body.T[:] = t_plate
    body.add(np.flatnonzero(kind == 1))

    part_nodes = np.unique(conn[kind == 2])
    saved, states, growth = {}, {}, []
    yield_room = mat["yield_MPa_by_temperature_C"][0][1]

    def read(label):
        u = body.displacement()
        stress, peeq = body.stress_and_plastic_strain()
        if comm.rank:
            return
        vm = von_mises(stress[kind == 2])
        mean_vm = vm.mean(axis=1)
        pe = peeq[kind == 2]
        states[label] = {
            "largest_displacement_mm": round(float(np.linalg.norm(u[part_nodes], axis=1).max()), 4),
            "von_mises_MPa": {"cell_mean_median": round(float(np.median(mean_vm)), 1), "cell_mean_p95": round(float(np.quantile(mean_vm, 0.95)), 1),
                              "integration_point_max": round(float(vm.max()), 1)},
            "share_of_part_cells_within_5_percent_of_room_yield": round(float((mean_vm > 0.95 * yield_room).mean()), 4),
            "equivalent_plastic_strain": {"median": round(float(np.median(pe)), 5), "p95": round(float(np.quantile(pe, 0.95)), 5),
                                          "max": round(float(pe.max()), 5)}}
        saved[label + "_u"] = u.astype(np.float32)
        full = np.zeros(len(conn), dtype=np.float32)
        full[kind == 2] = mean_vm
        saved[label + "_vm"] = full

    for j in range(lumps):
        new = np.flatnonzero(node_lump == j)
        live = np.flatnonzero((node_lump <= j) & (node_lump >= 0))
        body.T[new] = t_relax
        body.add(np.flatnonzero((lump == j) & (kind >= 2)))
        body.ramp(live, temps[j, live], increments, f"cool {j}")
        u = body.displacement()
        if comm.rank == 0:
            alive = part_nodes[node_lump[part_nodes] <= j]
            growth.append({"lump": j, "largest_displacement_mm": round(float(np.linalg.norm(u[alive], axis=1).max()), 4)})
    read("end_of_build_hot")
    everything = np.arange(len(xyz))
    body.ramp(everything, np.full(len(xyz), t_room), increments, "room temperature")
    read("room_temperature_on_plate")

    # release: plate and supports go; the part is held at three nodes (the same as build_sim.py)
    q = xyz[part_nodes]
    n1 = part_nodes[np.lexsort((q[:, 1], q[:, 0], q[:, 2]))[0]]
    n2 = part_nodes[np.argmax(np.abs(q[:, 0] - xyz[n1, 0]) - 0.01 * np.abs(q[:, 2] - xyz[n1, 2]))]
    n3 = part_nodes[np.argmax(np.abs(q[:, 1] - xyz[n1, 1]) - 0.01 * np.abs(q[:, 2] - xyz[n1, 2]))]
    for node, components in ((n1, (0, 1, 2)), (n2, (1, 2)), (n3, (2,))):
        for c in components:
            body.fixed[(int(node), c)] = True
    body.remove(np.flatnonzero(kind != 2))
    body.equilibrium("release")
    read("released")
    if comm.rank:
        return

    change = saved["released_u"][part_nodes] - saved["room_temperature_on_plate_u"][part_nodes]
    shape = remove_rigid(xyz[part_nodes], change.astype(np.float64))
    total = remove_rigid(xyz[part_nodes], saved["released_u"][part_nodes].astype(np.float64))
    r = xyz[part_nodes] - xyz[part_nodes].mean(axis=0)
    scale = float((total * r).sum() / (r * r).sum())
    warp = remove_rigid(xyz[part_nodes], total - scale * r)
    norm = np.linalg.norm(warp, axis=1)
    worst = int(np.argmax(norm))
    saved["released_warp"] = np.zeros((len(xyz), 3), dtype=np.float32)
    saved["released_warp"][part_nodes] = warp
    np.savez_compressed(out / "mechanics-fields.npz", **saved)
    report = {
        "schema": "935-cad-twin-build-sim-dolfinx/1", "date": time.strftime("%Y-%m-%d"), "level": level,
        "tool": f"DOLFINx {dolfinx.__version__}", "processes": comm.size, "linear_solver": solver,
        "temperature_increments_per_step": increments, "wall_seconds": round(time.time() - started, 1), "counts": body.counts,
        "nodes": int(len(xyz)), "cells": int(len(conn)), "unknowns": int(3 * len(xyz)),
        "stress_free_temperature_K": t_relax, "yield_MPa_by_temperature_C": mat["yield_MPa_by_temperature_C"],
        "largest_displacement_during_the_build_by_lump": growth, "states": states,
        "release": {"held_nodes": [int(n1) + 1, int(n2) + 1, int(n3) + 1],
                    "change_of_shape_at_release_largest_mm": round(float(np.linalg.norm(shape, axis=1).max()), 4),
                    "best_fit_uniform_shrinkage": round(scale, 6),
                    "distortion_after_release_rigid_motion_and_uniform_shrinkage_removed_mm": {
                        "largest": round(float(norm.max()), 4), "p95": round(float(np.quantile(norm, 0.95)), 4),
                        "median": round(float(np.median(norm)), 4),
                        "largest_at_build_coordinates_mm": [round(float(v), 1) for v in xyz[part_nodes][worst]]}}}
    (out / "mechanics.json").write_text(json.dumps(report, indent=1) + "\n")
    say(json.dumps({"wall_s": report["wall_seconds"], "counts": body.counts, "release": report["release"]}))


# --------------------------------------------------------------------------
# compare: this solver against CalculiX on the same mesh and temperatures (numpy only)


def compare(ccx_run_dir, dolfinx_dir, acceptance_file, out) -> None:
    """Both solvers' fields node by node, and the limits that were written before the first run."""

    ccx_run, mine = Path(ccx_run_dir), Path(dolfinx_dir)
    accept = json.loads(Path(acceptance_file).read_text())
    limits = accept["accept_when"]
    a, b = json.loads((mine / "mechanics.json").read_text()), json.loads((ccx_run / "mechanics.json").read_text())
    fa, fb = np.load(mine / "mechanics-fields.npz"), np.load(ccx_run / "mechanics-fields.npz")
    key = "distortion_after_release_rigid_motion_and_uniform_shrinkage_removed_mm"
    da, db = a["release"][key], b["release"][key]
    ratio = lambda x, y: round(float(x / y - 1.0), 5)
    room = "room_temperature_on_plate"
    rows = {
        "distortion_after_release_mm": {q: {"dolfinx": da[q], "calculix": db[q], "difference": ratio(da[q], db[q])} for q in ("median", "p95", "largest")},
        "largest_distortion_at_build_coordinates_mm": {"dolfinx": da["largest_at_build_coordinates_mm"], "calculix": db["largest_at_build_coordinates_mm"]},
        "uniform_shrinkage": {"dolfinx": a["release"]["best_fit_uniform_shrinkage"], "calculix": b["release"]["best_fit_uniform_shrinkage"],
                              "difference": ratio(a["release"]["best_fit_uniform_shrinkage"], b["release"]["best_fit_uniform_shrinkage"])},
        "von_mises_at_room_temperature_MPa": {q: {"dolfinx": a["states"][room]["von_mises_MPa"][q], "calculix": b["states"][room]["von_mises_MPa"][q],
                                                  "difference": ratio(a["states"][room]["von_mises_MPa"][q], b["states"][room]["von_mises_MPa"][q])}
                                              for q in ("cell_mean_median", "cell_mean_p95")},
        "node_by_node": {name: {"largest_difference": float(f"{np.abs(fa[name].astype(float) - fb[name].astype(float)).max():.3g}"),
                                "largest_value": round(float(np.abs(fb[name]).max()), 4)} for name in fb.files},
    }
    d, vm = rows["distortion_after_release_mm"], rows["von_mises_at_room_temperature_MPa"]
    checks = {
        "distortion_median_and_p95": max(abs(d["median"]["difference"]), abs(d["p95"]["difference"])) <= limits["distortion_after_release_median_and_p95_within"],
        "distortion_largest": abs(d["largest"]["difference"]) <= limits["distortion_after_release_largest_within"],
        "same_node": da["largest_at_build_coordinates_mm"] == db["largest_at_build_coordinates_mm"],
        "uniform_shrinkage": abs(rows["uniform_shrinkage"]["difference"]) <= limits["uniform_shrinkage_within"],
        "von_mises": max(abs(v["difference"]) for v in vm.values()) <= limits["von_mises_cell_mean_median_and_p95_at_room_temperature_within"],
    }
    record = {"level": a["level"], "acceptance": accept, "dolfinx": {k: a[k] for k in ("tool", "processes", "linear_solver", "temperature_increments_per_step", "wall_seconds", "counts")},
              "calculix_solver": b["solver"], **rows, "checks": {k: bool(v) for k, v in checks.items()}, "passed": bool(all(checks.values()))}
    Path(out).write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps({"passed": record["passed"], "checks": record["checks"]}))


# --------------------------------------------------------------------------
# record: what goes into the repository (numpy only)


def record(private_dir, ccx_record_file, acceptance_file, out) -> None:
    """Witness, the comparisons on the level both solvers ran, and the levels only this solver ran."""

    d = Path(private_dir)
    ccx = json.loads(Path(ccx_record_file).read_text())
    accept = json.loads(Path(acceptance_file).read_text())
    wit = json.loads((d / "witness" / "witness.json").read_text())
    key = "distortion_after_release_rigid_motion_and_uniform_shrinkage_removed_mm"
    comparisons = {}
    for solver in ("mumps", "blr", "gamg"):
        c = json.loads((d / f"compare-{REFERENCE_LEVEL}-{solver}.json").read_text())
        assert c["level"] == REFERENCE_LEVEL and c["dolfinx"]["linear_solver"] == solver and c["acceptance"] == accept
        comparisons[solver] = {k: v for k, v in c.items() if k not in ("level", "acceptance", "calculix_solver")}
        calculix_solver = c["calculix_solver"]
    levels = {}
    for run in sorted(d.glob("*/mechanics.json")):
        m = json.loads(run.read_text())
        if ccx["levels"][m["level"]]["mechanics"]:
            continue                                               # CalculiX ran it: it is a comparison, above
        assert m["level"] not in levels and m["linear_solver"] == "blr"
        model = ccx["levels"][m["level"]]["model"]
        assert model["nodes"] == m["nodes"] and sum(model["hexahedra"].values()) == m["cells"]
        levels[m["level"]] = {"cell_mm": model["cell_mm"], "lump_height_mm": model["lump_height_mm"], **{k: v for k, v in m.items() if k not in ("schema", "date", "level")}}
    reference = ccx["levels"][REFERENCE_LEVEL]
    ref = reference["mechanics"]["mechanics"]["release"][key]
    cell_size = []
    for name, lv in levels.items():
        if lv["lump_height_mm"] != reference["model"]["lump_height_mm"]:
            continue
        mine = lv["release"][key]
        cell_size.append({
            "lump_height_mm": lv["lump_height_mm"], "coarse": {"level": REFERENCE_LEVEL, "cell_mm": reference["model"]["cell_mm"], "solver": "CalculiX", **ref},
            "fine": {"level": name, "cell_mm": lv["cell_mm"], "solver": "DOLFINx", **mine},
            "fine_over_coarse": {q: round(mine[q] / ref[q] - 1.0, 4) for q in ("median", "p95", "largest")},
            "distance_between_the_two_largest_points_mm": round(float(np.linalg.norm(np.subtract(mine["largest_at_build_coordinates_mm"], ref["largest_at_build_coordinates_mm"]))), 1)})
    report = {
        "schema": "935-cad-twin-build-sim-dolfinx-record/1", "date": time.strftime("%Y-%m-%d"),
        "scope": ("The mechanics of the build screen solved a second time, by a second program: the cells, the lumps, the temperatures at the end of "
                  "each lump and the declared material are those of build_sim.py (params/build-sim-case.json, params/build-sim.json). Nothing here "
                  "is a new hypothesis; only the solver changes, and with it the size of model this host can run."),
        "tool": {"name": wit["tool"].split(",")[0], "image": IMAGE, "linear_algebra": "PETSc with MUMPS, as shipped in the image",
                 "licence": "LGPL-3.0-or-later (DOLFINx); used unmodified in its container, nothing of it is redistributed here"},
        "model": {"element": "8-node hexahedron, 2 x 2 x 2 integration points", "plasticity": "von Mises, linear isotropic hardening, radial return",
                  "temperature_of_a_cell": "the mean of its nodal temperatures, as CalculiX uses for its linear elements",
                  "birth": "a cell is added strain free at the displacements and temperature of that moment",
                  "increments_per_step": 2, "newton_stops_at": "1e-8 of the largest out-of-balance force seen"},
        "linear_solvers": {
            "mumps": "LU factorisation at every Newton iteration",
            "blr": (f"Cholesky factorisation with block low-rank compression (tolerance 1e-6) at the start of every increment, kept as the preconditioner of "
                    f"conjugate gradients (relative tolerance 1e-10) and made again when one solve takes more than {BLR_REFACTOR_ABOVE} iterations"),
            "gamg": "conjugate gradients on smoothed-aggregation multigrid with the six rigid motions as near-null space"},
        "witness": wit,
        "acceptance_file": Path(acceptance_file).name, "acceptance": accept,
        "comparison_with_calculix": {"level": REFERENCE_LEVEL, "calculix_solver": calculix_solver, "by_linear_solver": comparisons,
                                     "passed": bool(all(c["passed"] for c in comparisons.values()))},
        "levels": levels,
        "cell_size_at_the_same_lump_height": cell_size,
        "claims": ("a second solver reproduces the screen's numbers on the level both ran, and runs one level the first could not on this host. The "
                   "hypotheses, gates and limits of params/build-sim.json apply unchanged: voxel cells, lumps of many layers, a declared yield curve "
                   "and stress-free temperature, no measured distortion. Agreement of two solvers on one model says the equations are solved, not "
                   "that the model is the print."),
    }
    assert wit["passed"] and report["comparison_with_calculix"]["passed"]
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"levels": list(levels), "comparison_passed": report["comparison_with_calculix"]["passed"],
                      "cell_size": [(r["fine"]["level"], r["fine_over_coarse"]) for r in cell_size]}))


if __name__ == "__main__":
    {"witness": witness, "mechanics": mechanics, "compare": compare, "record": record}[sys.argv[1]](*sys.argv[2:])
