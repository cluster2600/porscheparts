#!/usr/bin/env python3
"""Thermal and thermoelastic solve of a tagged Gmsh mesh in DOLFINx, with witnesses and a render.

A template for the 935 head twin's agents, not a step of its chain. It shows the pattern every
new solver script of the twin follows: closed-form witnesses with acceptance fixed in the code,
then the case, then a record that carries hashes, solver statistics, an energy balance and the
limits of what it shows, then pictures for a visual reading.

  physics     steady (or backward-Euler transient) heat conduction with film conditions
              -k grad T . n = h (T - T_sink) on tagged facets; then linear thermoelasticity,
              one way: the temperature loads the solid, the solid does not heat.
  elements    P1 tetrahedra for both fields; one conductivity, modulus, Poisson ratio and
              expansion per tagged volume, constant in temperature.
  backend     cpu: PETSc AIJ, CG with BoomerAMG (heat) and GAMG (elasticity).
              cuda: the assembled matrix is converted to AIJCUSPARSE and solved with CG and
              GAMG on the GPU. It refuses to start when PETSc has no CUDA: the official DOLFINx
              image has none (PETSc 3.25.1 in dolfinx/dolfinx v0.11.0.post0). Assembly stays
              on the CPU either way.

Units: the mesh is read in millimetres (the twin's frame) and scaled to metres with
"mesh_unit_m"; the case is in SI with temperatures in degrees Celsius.

Usage (witness, demo-case and solve inside a DOLFINx image; render needs PyVista only):
  dolfinx_thermal_mech_template.py witness OUT_DIR [--backend cpu|cuda]
  dolfinx_thermal_mech_template.py demo-case OUT_DIR
  dolfinx_thermal_mech_template.py solve CASE.json MESH.msh OUT_DIR [--backend cpu|cuda]
  dolfinx_thermal_mech_template.py render OUT_DIR

  mpirun -n 4 python3 dolfinx_thermal_mech_template.py solve ...   runs the same solve in parallel.

demo-case writes a finned block and its case: plumbing for the agents, not the head. The head
mesh must carry one Gmsh physical group per film and per material; assembly_thermal.py assigns
its films by geometric rules at solve time and writes no such groups yet.

Nothing written here is an engine temperature, a stress allowable or a distortion prediction.
Every case value is a declared hypothesis unless the case names its source.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

SCHEMA_RECORD = "935-dolfinx-thermomech-template-record/1"
SCHEMA_CASE = "935-dolfinx-thermomech-case/1"
SCHEMA_WITNESS = "935-dolfinx-thermomech-template-witness/1"

# Acceptance of the witnesses, fixed before the first run.
W1_L2_REL_MAX = 2.0e-3      # steady slab with a uniform source, fine mesh, relative L2 error
W1_RATE_MIN = 1.7           # observed L2 convergence order between two meshes (P1: 2)
W2_REL_MAX = 0.02           # transient slab, end temperature against the Fourier series
W3_REL_MAX = 1.0e-5         # restrained bar under uniform heating: sigma_xx = -E alpha dT
BALANCE_MAX = 0.005         # head solve: |sum of film heat + source| / heat entering, steady only


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def log(msg: str) -> None:
    from mpi4py import MPI
    if MPI.COMM_WORLD.rank == 0:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- mesh

def read_msh(path: Path, unit_m: float):
    """Read a Gmsh .msh on rank 0, distribute it, scale it to metres. Returns (mesh, cell_tags, facet_tags)."""
    from mpi4py import MPI
    from dolfinx.io import gmsh as gmshio
    data = gmshio.read_from_msh(str(path), MPI.COMM_WORLD, rank=0, gdim=3)
    mesh = data.mesh
    mesh.geometry.x[:] *= unit_m
    if data.cell_tags is None or data.facet_tags is None:
        raise SystemExit(f"{path}: the mesh needs physical groups for its volumes and for its film facets")
    return mesh, data.cell_tags, data.facet_tags


def gmsh_box(path: Path, size, h: float) -> None:
    """A box [0,Lx]x[0,Ly]x[0,Lz] in mm with tagged faces: 1 x=0, 2 x=Lx, 3 y=0, 4 z=0, 5 the rest; volume 1."""
    from mpi4py import MPI
    if MPI.COMM_WORLD.rank == 0:
        import gmsh
        gmsh.initialize(["-nt", "1"])
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("box")
        lx, ly, lz = size
        gmsh.model.occ.addBox(0, 0, 0, lx, ly, lz)
        gmsh.model.occ.synchronize()
        e = 1e-6 * max(size)
        faces = {1: (-e, -e, -e, e, ly + e, lz + e), 2: (lx - e, -e, -e, lx + e, ly + e, lz + e),
                 3: (-e, -e, -e, lx + e, e, lz + e), 4: (-e, -e, -e, lx + e, ly + e, e)}
        used = set()
        for tag, box in faces.items():
            ents = [t for _, t in gmsh.model.getEntitiesInBoundingBox(*box, dim=2)]
            used.update(ents)
            gmsh.model.addPhysicalGroup(2, ents, tag)
        rest = [t for _, t in gmsh.model.getEntities(2) if t not in used]
        gmsh.model.addPhysicalGroup(2, rest, 5)
        gmsh.model.addPhysicalGroup(3, [t for _, t in gmsh.model.getEntities(3)], 1)
        gmsh.option.setNumber("Mesh.MeshSizeMax", h)
        gmsh.option.setNumber("Mesh.MeshSizeMin", h)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(path))
        gmsh.finalize()
    MPI.COMM_WORLD.barrier()


# ---------------------------------------------------------------- linear algebra

class Backend:
    """Where the Krylov solve runs. Assembly is on the CPU; on cuda the matrix is converted."""

    def __init__(self, name: str):
        from petsc4py import PETSc
        self.PETSc = PETSc
        self.name = name
        self.has_cuda = bool(PETSc.Sys.hasExternalPackage("cuda"))
        if name == "cuda" and not self.has_cuda:
            raise SystemExit("backend cuda refused: this PETSc was built without CUDA "
                             "(PETSc.Sys.hasExternalPackage('cuda') is False)")
        if name not in ("cpu", "cuda"):
            raise SystemExit(f"unknown backend {name}")

    def solve(self, A, b, uh, kind: str, rtol: float = 1e-10, nullspace=None) -> dict:
        """Solve A x = b into the dolfinx Function uh. kind: 'heat' or 'elasticity'."""
        PETSc = self.PETSc
        if self.name == "cuda":
            A = A.convert("aijcusparse")
        if nullspace is not None:
            A.setNearNullSpace(nullspace)
        x, rhs = A.createVecs()
        b.copy(rhs)
        ksp = PETSc.KSP().create(A.getComm())
        ksp.setOperators(A)
        ksp.setType("cg")
        ksp.setTolerances(rtol=rtol, atol=1e-30, max_it=5000)
        pc = ksp.getPC()
        if self.name == "cpu" and kind == "heat" and PETSc.Sys.hasExternalPackage("hypre"):
            pc.setType("hypre")
            pc.setHYPREType("boomeramg")
        else:
            pc.setType("gamg")
        ksp.setFromOptions()          # PETSC_OPTIONS in the environment can still override
        t0 = time.perf_counter()
        ksp.solve(rhs, x)
        seconds = time.perf_counter() - t0
        reason = ksp.getConvergedReason()
        if reason <= 0:
            raise SystemExit(f"{kind} solve did not converge: KSP reason {reason}")
        n = uh.function_space.dofmap.index_map.size_local * uh.function_space.dofmap.index_map_bs
        uh.x.array[:n] = x.getArray(readonly=True)[:n]
        uh.x.scatter_forward()
        stats = {"ksp": ksp.getType(), "pc": pc.getType(), "mat_type": A.getType(),
                 "iterations": ksp.getIterationNumber(), "converged_reason": int(reason),
                 "residual_norm": float(ksp.getResidualNorm()), "seconds": round(seconds, 3)}
        for obj in (ksp, x, rhs):
            obj.destroy()
        return stats


def assemble_system(a, L, bcs):
    import dolfinx.fem.petsc as fpetsc
    from petsc4py import PETSc
    A = fpetsc.assemble_matrix(a, bcs=bcs)
    A.assemble()
    b = fpetsc.assemble_vector(L)
    fpetsc.apply_lifting(b, [a], bcs=[bcs])
    b.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
    fpetsc.set_bc(b, bcs)
    return A, b


def rigid_body_modes(V):
    """Near null space of 3-D elasticity for GAMG (as in the DOLFINx elasticity demo)."""
    from petsc4py import PETSc
    from dolfinx import la
    imap, bs = V.dofmap.index_map, V.dofmap.index_map_bs
    basis = [la.vector(imap, bs=bs, dtype=PETSc.ScalarType) for _ in range(6)]
    arr = [v.array for v in basis]
    dofs = [V.sub(i).dofmap.list.ravel() for i in range(3)]
    x = V.tabulate_dof_coordinates()
    nodes = V.dofmap.list.ravel()
    x0, x1, x2 = x[nodes, 0], x[nodes, 1], x[nodes, 2]
    for i in range(3):
        arr[i][dofs[i]] = 1.0
    arr[3][dofs[0]], arr[3][dofs[1]] = -x1, x0
    arr[4][dofs[0]], arr[4][dofs[2]] = x2, -x0
    arr[5][dofs[2]], arr[5][dofs[1]] = x1, -x2
    la.orthonormalize(basis)
    vecs = [PETSc.Vec().createWithArray(a[: bs * imap.size_local], bsize=bs, comm=V.mesh.comm) for a in arr]
    return PETSc.NullSpace().create(vectors=vecs)


def scalar(form) -> float:
    from mpi4py import MPI
    from dolfinx import fem
    return MPI.COMM_WORLD.allreduce(fem.assemble_scalar(fem.form(form)), op=MPI.SUM)


# ---------------------------------------------------------------- physics

def cellwise(mesh, cell_tags, values: dict):
    """A DG0 function holding values[tag] on the cells of each tagged volume."""
    from dolfinx import fem
    Q = fem.functionspace(mesh, ("DG", 0))
    f = fem.Function(Q)
    missing = set(np.unique(cell_tags.values)) - set(values)
    if missing:
        raise SystemExit(f"volume tags without a material in the case: {sorted(int(t) for t in missing)}")
    for tag, v in values.items():
        f.x.array[cell_tags.find(tag)] = v
    f.x.scatter_forward()
    return f


def heat_problem(mesh, facet_tags, k, films: dict, fixed: dict, source=0.0, rho_c=None, dt=None, T_old=None):
    """Bilinear and linear forms of steady (or one backward-Euler step of) conduction with films.

    films: {facet_tag: (h W/m2K, T_sink C)}; fixed: {facet_tag: T C} (Dirichlet)."""
    import ufl
    from dolfinx import fem, mesh as dmesh
    V = fem.functionspace(mesh, ("Lagrange", 1))
    T, v = ufl.TrialFunction(V), ufl.TestFunction(V)
    ds = ufl.Measure("ds", domain=mesh, subdomain_data=facet_tags)
    a = k * ufl.inner(ufl.grad(T), ufl.grad(v)) * ufl.dx
    L = fem.Constant(mesh, float(source)) * v * ufl.dx
    for tag, (h, sink) in films.items():
        a += fem.Constant(mesh, float(h)) * T * v * ds(tag)
        L += fem.Constant(mesh, float(h * sink)) * v * ds(tag)
    if dt is not None:
        a += rho_c / dt * T * v * ufl.dx
        L += rho_c / dt * T_old * v * ufl.dx
    fdim = mesh.topology.dim - 1
    mesh.topology.create_connectivity(fdim, mesh.topology.dim)
    bcs = []
    for tag, value in fixed.items():
        dofs = fem.locate_dofs_topological(V, fdim, facet_tags.find(tag))
        bcs.append(fem.dirichletbc(float(value), dofs, V))
    return V, fem.form(a), fem.form(L), bcs


def thermoelastic(mesh, facet_tags, E, nu, alpha, dT, clamps: dict):
    """Forms of linear elasticity under the thermal strain alpha*dT. clamps: {facet_tag: components}."""
    import ufl
    from dolfinx import fem
    V = fem.functionspace(mesh, ("Lagrange", 1, (3,)))
    u, w = ufl.TrialFunction(V), ufl.TestFunction(V)
    lam = E * nu / ((1 + nu) * (1 - 2 * nu))
    mu = E / (2 * (1 + nu))
    eps = lambda z: ufl.sym(ufl.grad(z))
    I = ufl.Identity(3)
    sigma = lambda z: lam * ufl.tr(eps(z)) * I + 2 * mu * eps(z)
    thermal = (3 * lam + 2 * mu) * alpha * dT * I
    a = ufl.inner(sigma(u), eps(w)) * ufl.dx
    L = ufl.inner(thermal, eps(w)) * ufl.dx
    fdim = mesh.topology.dim - 1
    mesh.topology.create_connectivity(fdim, mesh.topology.dim)
    bcs = []
    for tag, comps in clamps.items():
        facets = facet_tags.find(tag)
        for c in comps:
            Vc, _ = V.sub(c).collapse()
            dofs = fem.locate_dofs_topological((V.sub(c), Vc), fdim, facets)
            zero = fem.Function(Vc)
            bcs.append(fem.dirichletbc(zero, dofs, V.sub(c)))
    stress = lambda uh: sigma(uh) - thermal
    return V, fem.form(a), fem.form(L), bcs, stress


def von_mises(mesh, s):
    """DG0 von Mises of the UFL stress s (Pa)."""
    import ufl
    from dolfinx import fem
    dev = s - ufl.tr(s) / 3 * ufl.Identity(3)
    Q = fem.functionspace(mesh, ("DG", 0))
    vm = fem.Function(Q)
    vm.interpolate(fem.Expression(ufl.sqrt(1.5 * ufl.inner(dev, dev)), Q.element.interpolation_points))
    return vm


# ---------------------------------------------------------------- witnesses

def witness(out_dir: Path, backend_name: str = "cpu") -> None:
    """Three closed forms, each through the same .msh import as the head."""
    import ufl
    import dolfinx
    from dolfinx import fem
    from mpi4py import MPI
    out_dir.mkdir(parents=True, exist_ok=True)
    be = Backend(backend_name)
    rows = []

    # W1: slab 0<x<L, T=T0 at both ends, uniform source q, insulated sides: T = T0 + q x (L - x) / 2k.
    # The order is taken on the effective cell size (volume / cells)^(1/3): on an unstructured mesh the
    # nominal Gmsh size does not halve the cells. A first run on nominal 4 and 2 mm meshes of this 10 mm
    # section read 1.49 (two cells across the coarse one); the meshes changed, the acceptance did not.
    L_mm, k, q, T0 = 40.0, 150.0, 2.0e7, 100.0
    errs, hs, h_eff, stats = [], [2.0, 1.0], [], None
    for h in hs:
        msh = out_dir / f"w1-slab-h{h:g}.msh"
        gmsh_box(msh, (L_mm, 10.0, 10.0), h)
        mesh, ct, ft = read_msh(msh, 1e-3)
        cells = mesh.comm.allreduce(mesh.topology.index_map(3).size_local, op=MPI.SUM)
        h_eff.append((L_mm * 10.0 * 10.0 / cells) ** (1 / 3))
        V, a, Lf, bcs = heat_problem(mesh, ft, fem.Constant(mesh, k), {}, {1: T0, 2: T0}, source=q)
        A, b = assemble_system(a, Lf, bcs)
        Th = fem.Function(V)
        stats = be.solve(A, b, Th, "heat")
        x = ufl.SpatialCoordinate(mesh)
        Lm = L_mm * 1e-3
        exact = T0 + q * x[0] * (Lm - x[0]) / (2 * k)
        errs.append(math.sqrt(scalar((Th - exact) ** 2 * ufl.dx) / scalar(exact ** 2 * ufl.dx)))
    rate = math.log(errs[0] / errs[1]) / math.log(h_eff[0] / h_eff[1])
    rows.append({"id": "W1-steady-slab-source", "expected": "T0 + q x (L - x) / (2 k)",
                 "relative_L2_error": [float(e) for e in errs], "mesh_size_mm": hs,
                 "effective_cell_size_mm": [round(v, 4) for v in h_eff], "observed_order": round(rate, 3),
                 "accept": {"relative_L2_error_fine_max": W1_L2_REL_MAX, "observed_order_min": W1_RATE_MIN},
                 "solver": stats, "passed": bool(errs[-1] <= W1_L2_REL_MAX and rate >= W1_RATE_MIN)})

    # W2: slab at T_init, face x=0 stepped to T1, others insulated; series solution at x=L, Fourier number 0.2.
    L_mm, k, rho_c, Ti, T1 = 20.0, 150.0, 2.4e6, 20.0, 220.0
    Lm, diff = L_mm * 1e-3, k / rho_c
    t_end, steps = 0.2 * Lm ** 2 / diff, 200
    dt = t_end / steps
    msh = out_dir / "w2-slab.msh"
    gmsh_box(msh, (L_mm, 4.0, 4.0), 1.0)
    mesh, ct, ft = read_msh(msh, 1e-3)
    Vt = fem.functionspace(mesh, ("Lagrange", 1))
    T_old = fem.Function(Vt)
    T_old.x.array[:] = Ti
    V, a, Lf, bcs = heat_problem(mesh, ft, fem.Constant(mesh, k), {}, {1: T1},
                                 rho_c=fem.Constant(mesh, rho_c), dt=fem.Constant(mesh, dt), T_old=T_old)
    import dolfinx.fem.petsc as fpetsc
    from petsc4py import PETSc
    A = fpetsc.assemble_matrix(a, bcs=bcs)
    A.assemble()
    Th = fem.Function(V)
    iters = 0
    for _ in range(steps):
        b = fpetsc.assemble_vector(Lf)
        fpetsc.apply_lifting(b, [a], bcs=[bcs])
        b.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
        fpetsc.set_bc(b, bcs)
        st = be.solve(A, b, Th, "heat")
        iters += st["iterations"]
        b.destroy()
        T_old.x.array[:] = Th.x.array
    def series(xv):
        return T1 + (Ti - T1) * sum(4 / ((2 * n + 1) * math.pi) * math.sin((2 * n + 1) * math.pi * xv / (2 * Lm))
                                    * math.exp(-((2 * n + 1) * math.pi / (2 * Lm)) ** 2 * diff * t_end)
                                    for n in range(200))
    expected = series(Lm)
    # Mean over the last 1 mm of the slab, against the series averaged over the same span.
    xs = np.linspace(Lm - 1e-3, Lm, 41)
    trapezoid = getattr(np, "trapezoid", None) or np.trapz
    expected_band = float(trapezoid([series(xv) for xv in xs], xs) / (xs[-1] - xs[0]))
    xc = ufl.SpatialCoordinate(mesh)[0]
    band = ufl.conditional(ufl.ge(xc, Lm - 1e-3), 1.0, 0.0)
    computed_band = scalar(Th * band * ufl.dx) / scalar(band * ufl.dx)
    rel = abs(computed_band - expected_band) / abs(Ti - T1)
    rows.append({"id": "W2-transient-slab-step", "expected": "Fourier series of the slab with one face stepped",
                 "fourier_number": 0.2, "steps": steps, "end_face_T_series_C": round(expected, 4),
                 "band_mean_T_series_C": round(expected_band, 4), "band_mean_T_computed_C": round(computed_band, 4),
                 "error_relative_to_step": round(rel, 6), "accept": {"error_relative_to_step_max": W2_REL_MAX},
                 "total_iterations": iters, "passed": bool(rel <= W2_REL_MAX)})

    # W3: bar heated uniformly, x held at both ends, rollers on y=0 and z=0: sigma_xx = -E alpha dT, others 0.
    E, nu, alpha, dT = 70e9, 0.33, 21e-6, 150.0
    msh = out_dir / "w3-bar.msh"
    gmsh_box(msh, (30.0, 8.0, 8.0), 2.0)
    mesh, ct, ft = read_msh(msh, 1e-3)
    V, a, Lf, bcs, stress = thermoelastic(mesh, ft, E, nu, alpha, fem.Constant(mesh, dT),
                                          {1: [0], 2: [0], 3: [1], 4: [2]})
    A, b = assemble_system(a, Lf, bcs)
    uh = fem.Function(V)
    st = be.solve(A, b, uh, "elasticity", rtol=1e-12, nullspace=rigid_body_modes(V))
    s = stress(uh)
    vol = scalar(fem.Constant(mesh, 1.0) * ufl.dx)
    sxx = scalar(s[0, 0] * ufl.dx) / vol
    syy = scalar(s[1, 1] * ufl.dx) / vol
    expected = -E * alpha * dT
    rel = max(abs(sxx - expected), abs(syy)) / abs(expected)
    rows.append({"id": "W3-restrained-bar-heated", "expected_sigma_xx_MPa": round(expected / 1e6, 4),
                 "computed_sigma_xx_MPa": round(sxx / 1e6, 6), "computed_sigma_yy_MPa": round(syy / 1e6, 9),
                 "relative_error": float(rel), "accept": {"relative_error_max": W3_REL_MAX},
                 "solver": st, "passed": bool(rel <= W3_REL_MAX)})

    record = {"schema": SCHEMA_WITNESS, "date": time.strftime("%Y-%m-%d"),
              "tool": {"dolfinx": dolfinx.__version__, "petsc": ".".join(map(str, be.PETSc.Sys.getVersion())),
                       "petsc_has_cuda": be.has_cuda, "backend": be.name, "mpi_ranks": MPI.COMM_WORLD.size},
              "witnesses": rows, "passed": all(r["passed"] for r in rows),
              "claims": "the import, the film and source terms, the time step and the thermal strain reproduce "
                        "three closed forms; this qualifies the template's software path, not a head result"}
    if MPI.COMM_WORLD.rank == 0:
        (out_dir / "witness.json").write_text(json.dumps(record, indent=1) + "\n")
    for r in rows:
        log(f"{r['id']}: {'pass' if r['passed'] else 'FAIL'}")
    if not record["passed"]:
        raise SystemExit(1)


# ---------------------------------------------------------------- the case

def demo_case(out_dir: Path) -> None:
    """A finned block with tagged films: plumbing for the agents, with no 935 value in it."""
    from mpi4py import MPI
    out_dir.mkdir(parents=True, exist_ok=True)
    if MPI.COMM_WORLD.rank == 0:
        import gmsh
        gmsh.initialize(["-nt", "1"])
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("finned-block")
        occ = gmsh.model.occ
        base = occ.addBox(-40, -30, 0, 80, 60, 12)
        fins = [(3, occ.addBox(-40, -30 + 8 * i, 12, 80, 3, 25)) for i in range(8)]
        occ.fuse([(3, base)], fins)
        occ.synchronize()
        e = 1e-3
        bottom = [t for _, t in gmsh.model.getEntitiesInBoundingBox(-41, -31, -e, 41, 31, e, dim=2)]
        rest = [t for _, t in gmsh.model.getEntities(2) if t not in bottom]
        gmsh.model.addPhysicalGroup(3, [t for _, t in gmsh.model.getEntities(3)], 1, name="block")
        gmsh.model.addPhysicalGroup(2, bottom, 11, name="hot_face")
        gmsh.model.addPhysicalGroup(2, rest, 12, name="air")
        gmsh.option.setNumber("Mesh.MeshSizeMax", 2.5)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(out_dir / "demo-block.msh"))
        gmsh.finalize()
        note = "demo value for the template's plumbing; not a 935 hypothesis and not a source"
        case = {
            "schema": SCHEMA_CASE,
            "what": "finned block, not the head: checks that tags, films, solver and render connect",
            "mesh_unit_m": 1e-3,
            "materials": {"1": {"name": "block", "conductivity_W_per_mK": 150.0, "youngs_modulus_GPa": 70.0,
                                "poisson": 0.33, "expansion_per_K": 21e-6, "status": note}},
            "films": {"11": {"name": "hot_face", "sink_temperature_C": 300.0, "coefficient_W_per_m2K": 500.0, "status": note},
                      "12": {"name": "air", "sink_temperature_C": 40.0, "coefficient_W_per_m2K": 80.0, "status": note}},
            "fixed_temperature": {},
            "mechanics": {"reference_temperature_C": 20.0, "clamps": {"11": [2]}, "pin_rigid_body": True, "status": note},
        }
        (out_dir / "demo-case.json").write_text(json.dumps(case, indent=1) + "\n")
    MPI.COMM_WORLD.barrier()


def check_case(case: dict) -> None:
    """Every material, film and support must say what it rests on; the twin admits no bare number."""
    if case.get("schema") != SCHEMA_CASE:
        raise SystemExit(f"case schema must be {SCHEMA_CASE}")
    blocks = list(case["materials"].values()) + list(case["films"].values()) + [case.get("mechanics", {"status": "-"})]
    blocks += list(case.get("fixed_temperature", {}).values())
    for blk in blocks:
        if not str(blk.get("status", "")).strip():
            raise SystemExit(f"case entry without a status or source: {json.dumps(blk)[:120]}")


def pin_rigid_body(mesh, V):
    """A 3-2-1 support: the node nearest the low corner of the bounding box held in x, y and z, the
    node nearest the +x corner in y and z, the node nearest the +y corner in z. It removes the six
    rigid-body motions and adds no stress to a body that is free to expand."""
    from mpi4py import MPI
    from dolfinx import fem
    comm = mesh.comm
    X = V.tabulate_dof_coordinates()
    lo = np.min(comm.allgather(X.min(axis=0)), axis=0)      # pickled MPI.MIN does not reduce arrays
    hi = np.max(comm.allgather(X.max(axis=0)), axis=0)
    targets = [(lo, (0, 1, 2)), (np.array([hi[0], lo[1], lo[2]]), (1, 2)), (np.array([lo[0], hi[1], lo[2]]), (2,))]
    bcs = []
    for target, comps in targets:
        dist = np.linalg.norm(X - target, axis=1)
        i = int(np.argmin(dist)) if len(dist) else -1
        best = comm.allreduce((float(dist[i]) if i >= 0 else math.inf, comm.rank), op=MPI.MIN)
        node = comm.bcast(X[i] if comm.rank == best[1] else None, root=best[1])
        for c in comps:
            Vc, _ = V.sub(c).collapse()
            dofs = fem.locate_dofs_geometrical((V.sub(c), Vc),
                                               lambda Y, p=node: np.linalg.norm(Y.T - p, axis=1) < 1e-9)
            bcs.append(fem.dirichletbc(fem.Function(Vc), dofs, V.sub(c)))
    return bcs


def solve(case_path: Path, msh_path: Path, out_dir: Path, backend_name: str = "cpu") -> None:
    import ufl
    import dolfinx
    from dolfinx import fem
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    out_dir.mkdir(parents=True, exist_ok=True)
    be = Backend(backend_name)
    case = json.loads(case_path.read_text())
    check_case(case)
    mesh, ct, ft = read_msh(msh_path, float(case["mesh_unit_m"]))
    mats = {int(t): m for t, m in case["materials"].items()}
    films = {int(t): (f["coefficient_W_per_m2K"], f["sink_temperature_C"]) for t, f in case["films"].items()}
    fixed = {int(t): f["temperature_C"] for t, f in case.get("fixed_temperature", {}).items()}
    present = set().union(*comm.allgather(set(np.unique(ft.values).tolist())))
    absent = sorted(t for t in list(films) + list(fixed) if t not in present)
    if absent:
        raise SystemExit(f"case names facet tags the mesh does not carry: {absent}")
    k = cellwise(mesh, ct, {t: m["conductivity_W_per_mK"] for t, m in mats.items()})
    log(f"mesh: {comm.allreduce(mesh.topology.index_map(3).size_local, op=MPI.SUM)} cells on {comm.size} ranks")

    V, a, Lf, bcs = heat_problem(mesh, ft, k, films, fixed)
    A, b = assemble_system(a, Lf, bcs)
    T = fem.Function(V, name="temperature_C")
    heat_stats = be.solve(A, b, T, "heat")
    log(f"heat: {heat_stats['iterations']} iterations, {heat_stats['seconds']} s on {heat_stats['mat_type']}")

    ds = ufl.Measure("ds", domain=mesh, subdomain_data=ft)
    by_film = {case["films"][str(t)].get("name", str(t)): scalar(fem.Constant(mesh, float(h)) * (sink - T) * ds(t))
               for t, (h, sink) in films.items()}
    area = {case["films"][str(t)].get("name", str(t)): scalar(fem.Constant(mesh, 1.0) * ds(t)) for t in films}
    entering = sum(q for q in by_film.values() if q > 0)
    imbalance = abs(sum(by_film.values())) / entering if entering > 0 else float("nan")
    if fixed:
        imbalance = float("nan")      # Dirichlet faces carry a reaction this balance does not read

    mech = case.get("mechanics")
    U = vm = None
    mech_stats = {}
    if mech:
        Tref = float(mech["reference_temperature_C"])
        E = cellwise(mesh, ct, {t: m["youngs_modulus_GPa"] * 1e9 for t, m in mats.items()})
        nu = cellwise(mesh, ct, {t: m["poisson"] for t, m in mats.items()})
        alpha = cellwise(mesh, ct, {t: m["expansion_per_K"] for t, m in mats.items()})
        Vu, au, Lu, bcu, stress = thermoelastic(mesh, ft, E, nu, alpha, T - Tref,
                                                {int(t): c for t, c in mech.get("clamps", {}).items()})
        if mech.get("pin_rigid_body"):
            bcu += pin_rigid_body(mesh, Vu)
        Au, bu = assemble_system(au, Lu, bcu)
        U = fem.Function(Vu, name="displacement_m")
        mech_stats = be.solve(Au, bu, U, "elasticity", nullspace=rigid_body_modes(Vu))
        vm = von_mises(mesh, stress(U))
        vm.name = "von_mises_Pa"
        log(f"elasticity: {mech_stats['iterations']} iterations, {mech_stats['seconds']} s")

    # Fields: .bp for ParaView (ADIOS2), and an .npz of the local pieces for the render step.
    from dolfinx.io import VTXWriter, has_adios2
    if has_adios2:
        with VTXWriter(comm, out_dir / "temperature.bp", [T], engine="BP4") as w:
            w.write(0.0)
        if U is not None:
            with VTXWriter(comm, out_dir / "displacement.bp", [U], engine="BP4") as w:
                w.write(0.0)
    write_render_input(out_dir / "fields.npz", T, U, vm)

    owned = T.x.array[: V.dofmap.index_map.size_local]
    Tlo, Thi = comm.allreduce(owned.min(), op=MPI.MIN), comm.allreduce(owned.max(), op=MPI.MAX)
    vol = scalar(fem.Constant(mesh, 1.0) * ufl.dx)
    record = {
        "schema": SCHEMA_RECORD, "date": time.strftime("%Y-%m-%d"),
        "inputs": {"case": str(case_path.name), "case_sha256": sha256(case_path),
                   "mesh": str(msh_path.name), "mesh_sha256": sha256(msh_path)},
        "tool": {"dolfinx": dolfinx.__version__, "petsc": ".".join(map(str, be.PETSc.Sys.getVersion())),
                 "petsc_has_cuda": be.has_cuda, "backend": be.name, "mpi_ranks": comm.size,
                 "elements": "P1 tetrahedra, temperature and displacement",
                 "bp_written": bool(has_adios2)},
        "heat": {"solver": heat_stats, "temperature_C": {"min": round(Tlo, 3), "max": round(Thi, 3),
                                                         "mean": round(scalar(T * ufl.dx) / vol, 3)},
                 "film_heat_W": {n: round(q, 4) for n, q in by_film.items()},
                 "film_area_mm2": {n: round(s * 1e6, 2) for n, s in area.items()},
                 "energy_imbalance": None if math.isnan(imbalance) else round(imbalance, 6),
                 "energy_balance_accept_max": BALANCE_MAX,
                 "energy_balance_passed": None if math.isnan(imbalance) else bool(imbalance <= BALANCE_MAX)},
        "claims": "a numerical result for the declared films, materials and supports of the case, on one mesh; "
                  "no mesh study, no correlation, not an engine temperature or stress",
        "limits": "constant properties, perfect contacts between tagged volumes, no radiation; "
                  "the energy balance checks the solve, not the case",
    }
    if U is not None:
        umag = np.linalg.norm(U.x.array.reshape(-1, 3)[: Vu.dofmap.index_map.size_local], axis=1)
        vloc = vm.x.array[: mesh.topology.index_map(3).size_local]
        record["mechanics"] = {"solver": mech_stats,
                               "displacement_max_mm": round(comm.allreduce(umag.max(), op=MPI.MAX) * 1e3, 5),
                               "von_mises_max_MPa": round(comm.allreduce(vloc.max(), op=MPI.MAX) / 1e6, 3),
                               "supports": mech.get("clamps"), "pin_rigid_body": bool(mech.get("pin_rigid_body")),
                               "note": "the peak sits at a support or a re-entrant corner until a mesh study says otherwise"}
    if comm.rank == 0:
        (out_dir / "record.json").write_text(json.dumps(record, indent=1) + "\n")
    log(f"record: {out_dir / 'record.json'}")
    if record["heat"]["energy_balance_passed"] is False:
        raise SystemExit(f"energy imbalance {imbalance:.4%} above {BALANCE_MAX:.1%}")


def write_render_input(path: Path, T, U, vm) -> None:
    """Gather each rank's VTK cells, points and values on rank 0 (ghost points repeat; harmless for a picture)."""
    from dolfinx import plot
    comm = T.function_space.mesh.comm
    topo, ctypes, geom = plot.vtk_mesh(T.function_space)
    n_cells = len(ctypes)
    piece = {"topology": topo, "cell_types": ctypes, "points": geom, "T": T.x.array.copy(),
             "U": None if U is None else U.x.array.reshape(-1, 3).copy(),
             "vm": None if vm is None else vm.x.array[:n_cells].copy()}
    pieces = comm.gather(piece, root=0)
    if comm.rank != 0:
        return
    tops, types, pts, Ts, Us, vms, offset = [], [], [], [], [], [], 0
    for p in pieces:
        t = p["topology"].reshape(-1, 5).copy()       # [4, i, j, k, l] per tetrahedron
        t[:, 1:] += offset
        tops.append(t.ravel())
        types.append(p["cell_types"])
        pts.append(p["points"])
        Ts.append(p["T"])
        if p["U"] is not None:
            Us.append(p["U"])
            vms.append(p["vm"])
        offset += len(p["points"])
    np.savez_compressed(path, topology=np.concatenate(tops), cell_types=np.concatenate(types),
                        points=np.concatenate(pts) * 1e3, temperature_C=np.concatenate(Ts),
                        displacement_mm=np.concatenate(Us) * 1e3 if Us else np.zeros((0, 3)),
                        von_mises_MPa=np.concatenate(vms) / 1e6 if vms else np.zeros(0))


# ---------------------------------------------------------------- render

def render(out_dir: Path) -> None:
    """Six views of the temperature and, if solved, two of von Mises on the deformed shape.

    Writes render-temperature.png, render-mechanics.png and render.json (hashes, ranges, what the
    reader must check). Run off screen: on WSL with GALLIUM_DRIVER=llvmpipe (see AGENT_TOOL_GUIDE.md)."""
    import pyvista as pv
    pv.OFF_SCREEN = True
    d = np.load(out_dir / "fields.npz")
    grid = pv.UnstructuredGrid(d["topology"], d["cell_types"], d["points"])
    grid.point_data["temperature_C"] = d["temperature_C"]
    out = {"schema": "935-dolfinx-thermomech-template-render/1", "images": {}}
    views = [("iso", (1, 1, 1)), ("iso-back", (-1, -1, 1)), ("+x", (1, 0, 0)), ("+y", (0, 1, 0)),
             ("-z", (0, 0, -1)), ("+z", (0, 0, 1))]
    surf = grid.extract_surface(algorithm=None)
    if not np.all(np.isfinite(d["temperature_C"])):
        raise SystemExit("temperature has non-finite values: no picture is drawn of a broken field")
    p = pv.Plotter(off_screen=True, shape=(2, 3), window_size=(1800, 1100))
    clim = [float(d["temperature_C"].min()), float(d["temperature_C"].max())]
    for i, (name, vec) in enumerate(views):
        p.subplot(i // 3, i % 3)
        p.add_text(name, font_size=10)
        p.add_mesh(surf, scalars="temperature_C", cmap="inferno", clim=clim,
                   scalar_bar_args={"title": "T (degC)", "n_labels": 5, "fmt": "%.0f", "vertical": True,
                                    "position_x": 0.84, "position_y": 0.15}, show_scalar_bar=(i == 0))
        p.view_vector(vec, viewup=(0, 1, 0) if vec[:2] == (0, 0) else (0, 0, 1))
        p.reset_camera()
    png = out_dir / "render-temperature.png"
    p.screenshot(str(png))
    p.close()
    out["images"]["temperature"] = {"file": png.name, "sha256": sha256(png), "range_C": clim}
    if len(d["displacement_mm"]):
        grid.point_data["displacement_mm"] = d["displacement_mm"]
        grid.cell_data["von_mises_MPa"] = d["von_mises_MPa"]
        umax = float(np.linalg.norm(d["displacement_mm"], axis=1).max())
        # The largest displacement drawn as 5% of the body's diagonal, and the undeformed edges in black:
        # without them a near-uniform thermal expansion looks like no deformation once the camera refits.
        diag = float(np.linalg.norm(np.ptp(d["points"], axis=0)))
        scale = 0.05 * diag / umax if umax > 0 else 1.0
        warped = grid.warp_by_vector("displacement_mm", factor=scale).extract_surface(algorithm=None)
        edges = surf.extract_feature_edges(feature_angle=40)
        p = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1600, 800))
        vlim = [0.0, float(np.percentile(d["von_mises_MPa"], 99))]
        for i, (name, vec) in enumerate(views[:2]):
            p.subplot(0, i)
            p.add_text(f"{name}: shape x{scale:.3g}, black = undeformed edges", font_size=10)
            p.add_mesh(warped, scalars="von_mises_MPa", cmap="viridis", clim=vlim, show_scalar_bar=(i == 0),
                       scalar_bar_args={"title": "vM MPa\n(p99 cap)", "vertical": True, "width": 0.06,
                                        "height": 0.5, "position_x": 0.92, "position_y": 0.25})
            p.add_mesh(edges, color="black", line_width=2)
            p.view_vector(vec)
            p.reset_camera()
        png = out_dir / "render-mechanics.png"
        p.screenshot(str(png))
        p.close()
        out["images"]["mechanics"] = {"file": png.name, "sha256": sha256(png), "displacement_max_mm": umax,
                                      "von_mises_p99_MPa": vlim[1], "deformation_scale": scale}
    out["reader_checks"] = [
        "the body is whole: no missing faces, holes or detached pieces against the mesh it came from",
        "the hottest region sits where the case puts the heat input, the coolest on the strongest film",
        "the colour bar range matches record.json (temperature min and max)",
        "no isolated hot or cold speck: a single-element extreme is a mesh or tag defect",
        "deformed shape: it departs from the black undeformed edges in the direction the heating predicts, "
        "smoothly, with no element turned inside out",
        "the stress peak at a support or a re-entrant corner is read as a singularity, not a stress",
    ]
    (out_dir / "render.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out["images"], indent=1))


def main(argv) -> None:
    if len(argv) < 2:
        raise SystemExit(__doc__)
    cmd, args = argv[1], argv[2:]
    backend = "cpu"
    if "--backend" in args:
        i = args.index("--backend")
        backend = args[i + 1]
        args = args[:i] + args[i + 2:]
    if cmd == "witness" and len(args) == 1:
        witness(Path(args[0]), backend)
    elif cmd == "demo-case" and len(args) == 1:
        demo_case(Path(args[0]))
    elif cmd == "solve" and len(args) == 3:
        solve(Path(args[0]), Path(args[1]), Path(args[2]), backend)
    elif cmd == "render" and len(args) == 1:
        render(Path(args[0]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except BaseException as exc:
        # One rank failing leaves the others waiting in a collective for ever; on a rented GPU that is
        # paid idle time. Abort the whole job instead.
        from mpi4py import MPI
        if MPI.COMM_WORLD.size > 1 and not (isinstance(exc, SystemExit) and exc.code in (0, None)):
            print(f"rank {MPI.COMM_WORLD.rank}: {exc!r}", file=sys.stderr, flush=True)
            MPI.COMM_WORLD.Abort(1)
        raise
