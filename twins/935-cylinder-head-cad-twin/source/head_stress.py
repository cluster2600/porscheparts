#!/usr/bin/env python3
"""Mechanical screen of the 935 head: cold assembly and hot firing, every candidate alloy (#703, #704, #705).

Placeholder header; the full description is written with the solver steps.

    head_stress.py thermal HP_WORK PARAMS_DIR OUT_DIR K [K ...]
        (cadsim image) the heat-path field of the ranking variant, solved again at each alloy
        conductivity K on the committed calibrated coefficients, kept at the head-alloy nodes

Nothing here is a measurement, a qualification or a release.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

THERMAL_VARIANT = "published_loading_oil"
LOAD_CASE = "mechanical-load-case.json"


def load_case(params) -> dict:
    return json.loads((Path(params) / LOAD_CASE).read_text())


def components(params) -> dict:
    """Valves, guides and plugs about the fitted axes (assembly_thermal.build_components)."""

    import assembly_thermal as at

    params = Path(params)
    base = json.loads((params / "assembly-case.json").read_text())
    return at.build_components(base, json.loads((params / "feature-fits.json").read_text()))


def cavity_mask(points, comps) -> np.ndarray:
    """Volume the head alloy does not hold in the mechanical model: the pressed-in guides and the plugs.

    The seat inserts stay head alloy, as in the thermal screens (H05, H10): no insert outside diameter is
    acquired, and inserts one millimetre wider than the valve heads would already overlap at the valve bridge.
    """

    import assembly_thermal as at

    out = np.zeros(len(points), dtype=bool)
    for v in comps["valves"].values():
        out |= at.guide_mask(points, v)
    for p in comps["plugs"].values():
        out |= at.plug_mask(points, p)
    return out


# ---------------------------------------------------------------- the head alloy as a smooth solid

def solid(body_dir, params, out_dir) -> None:
    """Body occupancy minus the declared cavities, smoothed, and its 0.5 iso-surface: the reference surface.

    The 0.25 mm occupancy of the v2 body is a binary grid. Its marching-cubes surface is a staircase whose
    steps are re-entrant corners at the voxel scale: a stress peak on them would measure the grid. The
    indicator is therefore smoothed by a Gaussian of declared width before the iso-surface is taken, which
    keeps flat faces where they are and rounds every edge and corner. That rounding is a hypothesis of
    this screen (its id is in the load case): no corner radius of the head is acquired.
    """

    import pyvista as pv
    from scipy import ndimage

    body_dir, params, out_dir = Path(body_dir), Path(params), Path(out_dir)
    lc = load_case(params)
    geo = lc["geometry"]
    sigma_mm = float(geo["smoothing"]["sigma_mm"]["value"])
    block = int(geo["smoothing"]["reference_block"])
    comps = components(params)
    grid = json.loads((body_dir / "occupancy-grid.json").read_text())
    body = np.load(body_dir / grid["array"], mmap_mode="r")
    h = grid["pitch_mm"]
    shape = body.shape
    x = grid["x0"] + h * np.arange(shape[0])
    y = grid["y0"] + h * np.arange(shape[1])
    field = np.zeros(shape, dtype=np.float32)
    removed = 0
    for k0 in range(0, shape[2], 8):
        k1 = min(k0 + 8, shape[2])
        z = grid["z0"] + h * np.arange(k0, k1)
        slab = np.asarray(body[:, :, k0:k1]) > 0.5
        points = np.stack(np.meshgrid(x, y, z, indexing="ij"), axis=-1).reshape(-1, 3)
        cav = cavity_mask(points, comps).reshape(slab.shape)
        removed += int((slab & cav).sum())
        field[:, :, k0:k1] = slab & ~cav
    ndimage.gaussian_filter(field, sigma=sigma_mm / h, output=field, mode="constant", cval=0.0, truncate=3.0)
    sx, sy, sz = (s // block * block for s in shape)
    coarse = field[:sx, :sy, :sz].reshape(sx // block, block, sy // block, block, sz // block, block).mean(axis=(1, 3, 5))
    del field
    coarse = np.pad(coarse, 1, constant_values=0.0)
    hc = h * block
    origin = np.array([grid["x0"], grid["y0"], grid["z0"]]) + h * (block - 1) / 2.0 - hc
    image = pv.ImageData(dimensions=coarse.shape, spacing=(hc, hc, hc), origin=origin)
    image.point_data["f"] = coarse.ravel(order="F")
    surf = image.contour([0.5], scalars="f", method="flying_edges").triangulate().clean()
    parts = surf.connectivity("largest")
    faces = parts.faces.reshape(-1, 4)[:, 1:]
    import trimesh

    mesh = trimesh.Trimesh(np.asarray(parts.points, dtype=float), faces, process=True)
    if mesh.volume < 0:
        mesh.invert()
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh.export(out_dir / "reference.stl")
    report = {"source_grid": str(body_dir / grid["array"]), "pitch_mm": h, "sigma_mm": sigma_mm,
              "reference_pitch_mm": hc, "iso_level": 0.5, "cavity_volume_removed_mm3": round(removed * h ** 3, 1),
              "triangles": int(len(mesh.faces)), "watertight": bool(mesh.is_watertight),
              "winding_consistent": bool(mesh.is_winding_consistent), "genus": int(round(1 - mesh.euler_number / 2)),
              "volume_mm3": round(float(mesh.volume), 1), "components_discarded": int(surf.connectivity("all").point_data["RegionId"].max())}
    (out_dir / "solid-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


# ---------------------------------------------------------------- thermal field, solved again

def thermal(hp_work, params, out_dir, *ks) -> None:
    """Solve the heat-path deck of the ranking variant at each conductivity and keep the head-alloy field.

    The mesh, the film groups and the joints are the prepared heat-path mesh (assembly_heat_paths.py
    prepare); the calibrated gas-side coefficients are the committed ones of the record. The solver
    run of 2026-11-20 kept no field, so the field is solved again; the peak must reproduce the record.
    """

    import assembly_heat_paths as ahp
    import sim_thermal

    hp_work, params, out_dir = Path(hp_work), Path(params), Path(out_dir)
    record = json.loads((params / "assembly-heat-paths.json").read_text())
    variant = record["variants"][THERMAL_VARIANT]
    prepared = json.loads((hp_work / "prepared.json").read_text())
    factor = {j: prepared["joints"][j]["area_factor"] for j in ahp.JOINTS if j in prepared["joints"]}
    npz = np.load(hp_work / "prepared.npz", allow_pickle=False)
    d = {k: npz[k] for k in ("joint", "group", "b_fid", "material", "split", "source", "xyz")}
    xyz = d["xyz"][d["source"]]
    node_mat = np.full(len(xyz), -1, dtype=np.int8)
    for i in range(len(ahp.MATERIALS)):
        node_mat[np.unique(d["split"][d["material"] == i])] = i
    alloy = np.flatnonzero(node_mat == 0)
    films = {name: (None if f is None else dict(f)) for name, f in variant["films"].items()}
    joints = {j: variant["joints_W_per_m2K"][j] * factor.get(j, 1.0) * 1.0e-6 for j in ahp.JOINTS}
    by_k = {r["alloy_conductivity_W_per_mK"]: r for r in variant["by_conductivity"]}
    out_dir.mkdir(parents=True, exist_ok=True)
    for k in (float(x) for x in ks):
        folder = out_dir / f"k{k:g}"
        folder.mkdir(parents=True, exist_ok=False)
        conductivity = {"alloy": k, **variant["conductivity_W_per_mK"]}
        ahp.write_job(folder / "head.inp", str(hp_work / "mesh.inc"), d, conductivity, films, joints)
        t0 = time.time()
        done = subprocess.run(["ccx", "-i", "head"], cwd=folder, capture_output=True, text=True,
                              env={"OMP_NUM_THREADS": "1", "CCX_NPROC_EQUATION_SOLVER": "1", "PATH": "/usr/bin:/bin"})
        (folder / "ccx.log").write_text(done.stdout[-20000:] + done.stderr[-20000:])
        if done.returncode or not (folder / "head.frd").exists():
            raise SystemExit(f"k{k:g}: ccx returned {done.returncode}")
        temps = sim_thermal.read_frd_temperatures(folder / "head.frd")
        for name in ("head.frd", "head.dat", "head.12d", "head.cvg", "head.sta"):
            (folder / name).unlink(missing_ok=True)
        if len(temps) != len(xyz):
            raise SystemExit(f"k{k:g}: {len(temps)} temperatures for {len(xyz)} nodes")
        t_alloy = temps[alloy]
        np.savez_compressed(folder / "alloy-field.npz", xyz=xyz[alloy].astype(np.float32),
                            temperature_C=t_alloy.astype(np.float32))
        recorded = by_k.get(k, {}).get("peak_C", {}).get("alloy")
        report = {"alloy_conductivity_W_per_mK": k, "alloy_nodes": int(len(alloy)),
                  "peak_alloy_C": round(float(t_alloy.max()), 2), "mean_alloy_C": round(float(t_alloy.mean()), 2),
                  "peak_alloy_at_mm": [round(float(x), 1) for x in xyz[alloy][int(np.argmax(t_alloy))]],
                  "recorded_peak_alloy_C": recorded,
                  "reproduces_record_within_C": None if recorded is None else round(abs(float(t_alloy.max()) - recorded), 3),
                  "ccx_s": round(time.time() - t0, 1)}
        (folder / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)


def remesh(reference, out_stl, report, size_mm, max_dist_mm="0.2", zones_json="") -> None:
    """Isotropic remeshing of the reference surface (pymeshlab, recon image): one mesh level.

    Every vertex is reprojected onto the reference, and no edge collapse may leave it by more than the
    declared surface distance. ``zones_json`` lists refinement zones {"centre": [x, y, z], "radius_mm",
    "size_mm"}; the faces of each zone are remeshed first at its size (smallest size first), then the rest
    at ``size_mm``; the border of a zone is kept, so the levels nest.
    """

    import pymeshlab

    size = float(size_mm)
    zones = json.loads(Path(zones_json).read_text()) if zones_json else []
    max_dist = float(max_dist_mm)
    t0 = time.time()

    def within(zone_list):
        def test(c):
            out = np.zeros(len(c), dtype=bool)
            for z in zone_list:
                out |= np.linalg.norm(c - np.asarray(z["centre"]), axis=1) <= z["radius_mm"]
            return out
        return test

    def once(zone_list):
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(str(reference))

        def remesh_where(target, select):
            mm = ms.current_mesh()
            v, f = mm.vertex_matrix(), mm.face_matrix()
            if select is not None:
                chosen = select(v[f].mean(axis=1))
                if not chosen.any():
                    return
                ms.add_mesh(pymeshlab.Mesh(vertex_matrix=v, face_matrix=f, f_scalar_array=chosen.astype(float)), "work")
                ms.compute_selection_by_condition_per_face(condselect="(fq > 0.5)")
            ms.meshing_isotropic_explicit_remeshing(iterations=8, adaptive=False, selectedonly=select is not None,
                                                    targetlen=pymeshlab.PureValue(target), featuredeg=60.0,
                                                    checksurfdist=True, maxsurfdist=pymeshlab.PureValue(max_dist),
                                                    reprojectflag=True)

        # Smallest size first; each zone leaves out the faces of smaller zones, already remeshed.
        ordered = sorted(zone_list, key=lambda z: z["size_mm"])
        for i, zone in enumerate(ordered):
            finer = [z for z in ordered[:i] if z["size_mm"] < zone["size_mm"]]
            remesh_where(float(zone["size_mm"]), lambda c, z=zone, fz=finer: within([z])(c) & ~within(fz)(c))
        remesh_where(size, (lambda c: ~within(ordered)(c)) if ordered else None)
        ms.meshing_remove_duplicate_vertices()
        ms.meshing_remove_unreferenced_vertices()
        ms.compute_selection_by_self_intersections_per_face()
        mm = ms.current_mesh()
        sel = mm.face_selection_array()
        return ms, mm.vertex_matrix()[mm.face_matrix()[sel]].mean(axis=1)

    # Where two faces cross (two close surfaces, an edge longer than the gap), the faces within 4 mm are
    # remeshed at half the size and the level is built again from the reference; the repairs are recorded.
    repairs = []
    for attempt in range(5):
        ms, crossing = once(zones + repairs)
        if not len(crossing):
            break
        for c in crossing:
            if not any(np.linalg.norm(c - np.asarray(r["centre"])) < 2.0 for r in repairs):
                repairs.append({"centre": [round(float(x), 2) for x in c], "radius_mm": 4.0,
                                "size_mm": round(min(size / 2.0, 1.0), 3), "why": "self-intersection repair"})
    topo = ms.get_topological_measures()
    ms.save_current_mesh(str(out_stl), binary=True)
    mm = ms.current_mesh()
    v, f = mm.vertex_matrix(), mm.face_matrix()
    edges = np.linalg.norm(v[f[:, [1, 2, 0]]] - v[f], axis=2).ravel()
    rep = {"reference": str(reference), "size_mm": size, "zones": zones, "repairs": repairs, "attempts": attempt + 1,
           "max_surface_distance_mm": max_dist, "faces": mm.face_number(),
           "edge_mm_p5_p50_p95": [round(float(x), 3) for x in np.percentile(edges, [5, 50, 95])],
           "boundary_edges": topo["boundary_edges"], "non_manifold_edges": topo["non_two_manifold_edges"],
           "genus": topo.get("genus"), "self_intersecting_faces": int(len(crossing)), "remesh_s": round(time.time() - t0, 1)}
    Path(report).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))
    if len(crossing):
        raise SystemExit("self-intersections left after the repairs")


def tetmesh(surface, out_npz, report, size_max_mm) -> None:
    """Gmsh HXT tetrahedra inside a remeshed level surface (cadsim or DOLFINx image): linear tets, P1 geometry."""

    import gmsh

    t0 = time.time()
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", 4)
    gmsh.merge(str(surface))
    surf = gmsh.model.getEntities(2)
    loop = gmsh.model.geo.addSurfaceLoop([s[1] for s in surf])
    gmsh.model.geo.addVolume([loop])
    gmsh.model.geo.synchronize()
    gmsh.option.setNumber("Mesh.MeshSizeMax", float(size_max_mm))
    gmsh.option.setNumber("Mesh.MeshSizeMin", 0.1)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
    gmsh.option.setNumber("Mesh.Algorithm3D", 10)
    gmsh.option.setNumber("Mesh.Optimize", 1)
    gmsh.model.mesh.generate(3)
    tag, nodes, _ = gmsh.model.mesh.getNodes()
    order = np.argsort(tag)
    tag = np.asarray(tag)[order]
    xyz = nodes.reshape(-1, 3)[order]
    etypes, etags, enodes = gmsh.model.mesh.getElements(3)
    i = list(etypes).index(4)
    tets = np.searchsorted(tag, np.asarray(enodes[i], dtype=np.int64).reshape(-1, 4))
    q = np.asarray(gmsh.model.mesh.getElementQualities(np.asarray(etags[i]).tolist(), "minSICN"))
    gmsh.finalize()
    used = np.unique(tets)
    remap = np.full(len(xyz), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    xyz, tets = xyz[used], remap[tets]
    p = xyz[tets]
    vol = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p[:, 3] - p[:, 0]) / 6.0
    flip = vol < 0
    tets[flip] = tets[flip][:, [0, 2, 1, 3]]
    pairs = np.sort(np.concatenate([tets[:, [a, b]] for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))]), axis=1)
    edges = np.unique(pairs[:, 0] * len(xyz) + pairs[:, 1])
    np.savez_compressed(out_npz, xyz=xyz, tets=tets.astype(np.int32))
    rep = {"surface": str(surface), "size_max_mm": float(size_max_mm), "nodes": int(len(xyz)), "tets": int(len(tets)),
           "edges": int(len(edges)), "p2_dofs": int(3 * (len(xyz) + len(edges))),
           "volume_mm3": round(float(np.abs(vol).sum()), 1), "minSICN_p1": round(float(np.percentile(q, 1)), 4),
           "share_minSICN_below_0p1": round(float((q < 0.1).mean()), 6), "min_minSICN": round(float(q.min()), 5),
           "mesh_s": round(time.time() - t0, 1)}
    Path(report).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))


# ---------------------------------------------------------------- linear elasticity in DOLFINx: P2 tetrahedra

E_REF = 70000.0       # MPa: the modulus of every unit case; the stress of a force case does not depend on it
ALPHA_REF = 1.0e-5    # 1/K: the expansion of every thermal unit case; a thermal stress scales with E alpha
T_REF = 20.0          # degC: the strain-free temperature (assembly at room temperature)
REF_VERTICES = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
VOIGT = ((0, 0), (1, 1), (2, 2), (0, 1), (1, 2), (0, 2))     # xx yy zz xy yz xz


class Elastic:
    """Small-strain isotropic elasticity on P1-geometry tetrahedra with quadratic displacement.

    One stiffness, factorised once; unit load cases are right-hand sides: pressures and tractions on
    tagged boundary faces, a thermal strain from a nodal temperature field, zero displacement on
    tagged faces and at named vertices. Stresses are returned at the vertices, averaged over the cells
    that share a vertex with the cell volume as weight.
    """

    def __init__(self, xyz, tets, faces, face_group, n_groups, nu, solver="mumps", log=print):
        from mpi4py import MPI
        from petsc4py import PETSc
        import basix.ufl
        import ufl
        from dolfinx import fem, graph, io, mesh as dmesh
        import dolfinx.fem.petsc as fpetsc

        self.MPI, self.PETSc, self.fem, self.fpetsc, self.ufl = MPI, PETSc, fem, fpetsc, ufl
        self.comm = comm = MPI.COMM_WORLD
        self.rank = comm.rank
        self.log = log
        self.n_nodes = len(xyz) if self.rank == 0 else 0
        self.n_nodes = comm.bcast(self.n_nodes, root=0)
        element = basix.ufl.element("Lagrange", "tetrahedron", 1, shape=(3,))
        cells = np.asarray(tets, dtype=np.int64) if self.rank == 0 else np.zeros((0, 4), dtype=np.int64)
        points = np.asarray(xyz, dtype=np.float64) if self.rank == 0 else np.zeros((0, 3))
        self.mesh = msh = dmesh.create_mesh(comm, cells, element, points)
        tdim = 3
        msh.topology.create_connectivity(tdim - 1, tdim)
        msh.topology.create_connectivity(tdim, 0)
        msh.topology.create_connectivity(0, tdim)
        cmap = msh.topology.index_map(tdim)
        self.nc_owned = cmap.size_local
        self.nc_local = cmap.size_local + cmap.num_ghosts
        self.gmap = np.asarray(msh.geometry.input_global_indices, dtype=np.int64)
        self.geo = np.asarray(msh.geometry.dofmaps[0][:self.nc_local])
        self.cell_vertex = np.asarray(msh.topology.connectivity(tdim, 0).array, dtype=np.int32).reshape(-1, 4)[:self.nc_local]

        # boundary faces by input vertex ids -> local facet tags
        f_in = np.asarray(faces, dtype=np.int64) if self.rank == 0 else np.zeros((0, 3), dtype=np.int64)
        v_in = np.asarray(face_group, dtype=np.int32) if self.rank == 0 else np.zeros(0, dtype=np.int32)
        ent, val = io.distribute_entity_data(msh, tdim - 1, f_in, v_in)
        self.tags = dmesh.meshtags_from_entities(msh, tdim - 1, graph.adjacencylist(ent.astype(np.int32)),
                                                 np.asarray(val, dtype=np.int32))
        self.V = V = fem.functionspace(msh, ("Lagrange", 2, (3,)))
        self.S = S = fem.functionspace(msh, ("Lagrange", 1))
        sd = np.asarray(S.dofmap.list[:self.nc_local])
        n_s = S.dofmap.index_map.size_local + S.dofmap.index_map.num_ghosts
        self.s_in = np.full(n_s, -1, dtype=np.int64)
        self.s_in[sd.ravel()] = self.gmap[self.geo.ravel()]
        assert (self.s_in >= 0).all()
        self.T = fem.Function(S)
        self.T.x.array[:] = T_REF
        self.alpha = fem.Constant(msh, 0.0)
        self.p = [fem.Constant(msh, 0.0) for _ in range(n_groups + 1)]
        self.q = [fem.Constant(msh, np.zeros(3)) for _ in range(n_groups + 1)]
        mu = E_REF / (2.0 * (1.0 + nu))
        lam = E_REF * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
        eye = ufl.Identity(3)

        def eps(w):
            return ufl.sym(ufl.grad(w))

        def sig(w):
            return 2.0 * mu * eps(w) + lam * ufl.tr(eps(w)) * eye

        u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
        self.u = fem.Function(V)
        th = (3.0 * lam + 2.0 * mu) * self.alpha * (self.T - T_REF) * eye
        n = ufl.FacetNormal(msh)
        ds = ufl.Measure("ds", domain=msh, subdomain_data=self.tags)
        dx = ufl.Measure("dx", domain=msh)
        L = ufl.inner(th, eps(v)) * dx
        for g in range(1, n_groups + 1):
            L += ufl.inner(-self.p[g] * n + self.q[g], v) * ds(g)
        self.a = fem.form(ufl.inner(sig(u), eps(v)) * dx)
        self.L = fem.form(L)
        self.x_stress = fem.Expression(sig(self.u) - th, REF_VERTICES)
        self.bcs = []
        self.solver = solver

    def local_vertex(self, input_ids):
        """Local vertex entities of the given input vertices that this process holds."""

        want = np.asarray(input_ids, dtype=np.int64)
        hit = np.isin(self.gmap[self.geo], want)
        return np.unique(self.cell_vertex[hit]).astype(np.int32)

    def fix(self, face_groups=(), component_faces=(), vertices=()):
        """Zero displacement: ``component_faces`` = [(component, group)], ``vertices`` = [(input id, components)]."""

        fem = self.fem
        V = self.V
        zero = self.PETSc.ScalarType(0.0)
        for c, g in component_faces:
            facets = self.tags.find(g)
            dofs = fem.locate_dofs_topological(V.sub(c), 2, facets)
            self.bcs.append(fem.dirichletbc(zero, dofs, V.sub(c)))
        for node, comps in vertices:
            ents = self.local_vertex([node])
            for c in comps:
                dofs = fem.locate_dofs_topological(V.sub(c), 0, ents)
                self.bcs.append(fem.dirichletbc(zero, dofs, V.sub(c)))

    def factorise(self):
        PETSc, fpetsc = self.PETSc, self.fpetsc
        t0 = time.time()
        self.A = fpetsc.assemble_matrix(self.a, bcs=self.bcs)
        self.A.assemble()
        self.ksp = ksp = PETSc.KSP().create(self.comm)
        ksp.setOperators(self.A)
        ksp.setType("preonly")
        pc = ksp.getPC()
        pc.setType("cholesky")
        pc.setFactorSolverType("mumps")
        opts = PETSc.Options()
        opts["mat_mumps_icntl_14"] = 80
        ksp.setFromOptions()
        self.A.setOption(PETSc.Mat.Option.SPD, True)
        ksp.setUp()
        self.factor_s = time.time() - t0
        self.dofs = self.V.dofmap.index_map.size_global * 3
        self.log(f"factorised {self.dofs} dofs in {self.factor_s:.1f} s")

    def set_temperature(self, by_input_node):
        self.T.x.array[:] = np.asarray(by_input_node)[self.s_in]

    def solve(self, pressures=None, tractions=None, thermal=False):
        """One unit case: pressures {group: MPa}, tractions {group: vector MPa}, thermal strain on or off."""

        PETSc, fpetsc = self.PETSc, self.fpetsc
        for c in self.p:
            c.value = 0.0
        for c in self.q:
            c.value = np.zeros(3)
        for g, val in (pressures or {}).items():
            self.p[g].value = float(val)
        for g, val in (tractions or {}).items():
            self.q[g].value = np.asarray(val, dtype=float)
        self.alpha.value = ALPHA_REF if thermal else 0.0
        b = fpetsc.assemble_vector(self.L)
        fpetsc.apply_lifting(b, [self.a], bcs=[self.bcs])
        b.ghostUpdate(addv=PETSc.InsertMode.ADD, mode=PETSc.ScatterMode.REVERSE)
        fpetsc.set_bc(b, self.bcs)
        t0 = time.time()
        self.ksp.solve(b, self.u.x.petsc_vec)
        self.u.x.scatter_forward()
        assert self.ksp.getConvergedReason() > 0, self.ksp.getConvergedReason()
        r = b.copy()
        self.A.mult(self.u.x.petsc_vec, r)
        r.axpy(-1.0, b)
        rel = r.norm() / max(b.norm(), 1e-300)
        b.destroy()
        r.destroy()
        return time.time() - t0, rel

    def vertex_stress(self):
        """Six stress components at every input vertex (rank 0; None elsewhere), volume-weighted over cells."""

        cells = np.arange(self.nc_owned, dtype=np.int32)
        vals = self.x_stress.eval(self.mesh, cells).reshape(len(cells), 4, 3, 3)
        six = np.stack([vals[:, :, i, j] for i, j in VOIGT], axis=-1)            # (cells, 4, 6)
        x = self.mesh.geometry.x[self.geo[:self.nc_owned]]
        vol = np.abs(np.einsum("ij,ij->i", np.cross(x[:, 1] - x[:, 0], x[:, 2] - x[:, 0]), x[:, 3] - x[:, 0])) / 6.0
        ids = self.gmap[self.geo[:self.nc_owned]]
        parts = self.comm.gather((ids, six.astype(np.float64), vol), root=0)
        if self.rank:
            return None
        acc = np.zeros((self.n_nodes, 6))
        wsum = np.zeros(self.n_nodes)
        for ids, six, vol in parts:
            w = np.repeat(vol, 4)
            np.add.at(acc, ids.ravel(), six.reshape(-1, 6) * w[:, None])
            np.add.at(wsum, ids.ravel(), w)
        return acc / np.maximum(wsum, 1e-300)[:, None]

    def displacement_at(self, input_ids):
        """Displacement of the P2 field at given input vertices (rank 0)."""

        from dolfinx import geometry
        if self.rank == 0:
            pts = None
        out = []
        V1 = self.fem.functionspace(self.mesh, ("Lagrange", 1, (3,)))
        u1 = self.fem.Function(V1)
        u1.interpolate(self.u)
        vd = np.asarray(V1.dofmap.list[:self.nc_local])
        node_in = np.full(V1.dofmap.index_map.size_local + V1.dofmap.index_map.num_ghosts, -1, dtype=np.int64)
        node_in[vd.ravel()] = self.gmap[self.geo.ravel()]
        arr = u1.x.array.reshape(-1, 3)
        own = V1.dofmap.index_map.size_local
        sel = np.isin(node_in[:own], np.asarray(input_ids))
        parts = self.comm.gather((node_in[:own][sel], arr[:own][sel].copy()), root=0)
        if self.rank:
            return None
        got = {}
        for ids, vals in parts:
            for i, val in zip(ids, vals):
                got[int(i)] = val
        return np.array([got[int(i)] for i in input_ids])


def von_mises(s):
    s = np.asarray(s)
    return np.sqrt(0.5 * ((s[..., 0] - s[..., 1]) ** 2 + (s[..., 1] - s[..., 2]) ** 2 + (s[..., 2] - s[..., 0]) ** 2)
                   + 3.0 * (s[..., 3] ** 2 + s[..., 4] ** 2 + s[..., 5] ** 2))


def principal(s):
    """Largest and smallest principal stresses of Voigt rows (xx yy zz xy yz xz)."""

    s = np.asarray(s)
    m = np.empty(s.shape[:-1] + (3, 3))
    for k, (i, j) in enumerate(VOIGT):
        m[..., i, j] = s[..., k]
        m[..., j, i] = s[..., k]
    w = np.linalg.eigvalsh(m)
    return w[..., -1], w[..., 0]


def boundary_faces(tets):
    """Faces that belong to one tetrahedron, oriented outward."""

    t = np.asarray(tets, dtype=np.int64)
    local = ((1, 2, 3), (0, 3, 2), (0, 1, 3), (0, 2, 1))       # outward for a positively oriented tet
    f = np.concatenate([t[:, list(l)] for l in local])
    key = np.sort(f, axis=1)
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return f[counts[inverse.ravel()] == 1]


def face_geometry(xyz, faces):
    p = xyz[faces]
    cr = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    area = 0.5 * np.linalg.norm(cr, axis=1)
    return p.mean(axis=1), cr / np.maximum(2.0 * area, 1e-300)[:, None], area


# ---------------------------------------------------------------- one mesh level: load faces, holds, temperatures

GROUPS = ("support", "nut_x_minus_y_minus", "nut_x_minus_y_plus", "nut_x_plus_y_minus", "nut_x_plus_y_plus",
          "chamber", "seat_inlet", "seat_exhaust", "guide_inlet", "guide_exhaust", "thread_plug_x_plus",
          "thread_plug_x_minus")
STUDS = ("stud_x_minus_y_minus", "stud_x_minus_y_plus", "stud_x_plus_y_minus", "stud_x_plus_y_plus")


def stud_seats(params) -> list:
    """Axis and nut-seat level of each head stud, from the fitted passages and counterbores (feature-fits.json)."""

    fits = {r["id"]: r["fit"] for r in json.loads((Path(params) / "feature-fits.json").read_text())["regions"]}
    out = []
    for s in STUDS:
        cb, ps = fits[f"{s}_counterbore"], fits[f"{s}_passage"]
        d = np.asarray(cb["axis_direction"], dtype=float)
        ends = [np.asarray(cb["axis_point"]) + t * d for t in cb["station_range_mm"]]
        floor = min(ends, key=lambda e: e[2])
        out.append({"stud": s, "axis_xy": [float(floor[0]), float(floor[1])], "floor_z_mm": float(floor[2]),
                    "passage_radius_mm": 0.5 * ps["diameter_mm"], "counterbore_radius_mm": 0.5 * cb["diameter_mm"]})
    return out


def classify_faces(xyz, faces, params) -> tuple:
    """Group of every boundary face (index into GROUPS + 1; 0 = free surface) and the rule values used."""

    import assembly_thermal as at

    lc = load_case(params)
    hold = lc["holds"]
    comps = components(params)
    c, n, area = face_geometry(xyz, faces)
    group = np.zeros(len(faces), dtype=np.int32)
    rho0 = np.hypot(c[:, 0], c[:, 1])
    z_floor, r_bore, r_collar = (hold["register_floor_z_mm"]["value"], hold["bore_radius_mm"]["value"],
                                 hold["collar_radius_mm"]["value"])
    support = (np.abs(c[:, 2] - z_floor) < 0.75) & (n[:, 2] < -0.9) & (rho0 > r_bore + 0.3) & (rho0 < r_collar - 0.3)
    group[support] = GROUPS.index("support") + 1
    r_nut = 0.5 * lc["studs"]["nut_bearing_diameter_mm"]["value"]
    seats = stud_seats(params)
    for s in seats:
        rs = np.hypot(c[:, 0] - s["axis_xy"][0], c[:, 1] - s["axis_xy"][1])
        sel = (n[:, 2] > 0.9) & (rs > s["passage_radius_mm"] + 0.25) & (rs < r_nut) & (np.abs(c[:, 2] - s["floor_z_mm"]) < 2.0)
        group[sel & (group == 0)] = GROUPS.index("nut_" + s["stud"][5:]) + 1
    chamber = (rho0 < r_bore - 0.3) & (c[:, 2] > z_floor - 0.5) & (c[:, 2] < lc["gas"]["chamber_z_max_mm"]["value"]) & (n[:, 2] < 0.3)
    behind = np.zeros(len(faces), dtype=bool)
    for name, v in comps["valves"].items():
        d = np.asarray(v["direction"])
        t, rho = at.axis_coordinates(c, v["origin"], d)
        behind |= (rho < v["r_head"] + 0.3) & (t > v["t_face"] - 1.0)
        radial = (c - np.asarray(v["origin"]) - np.outer(t, d)) / np.maximum(rho, 1e-9)[:, None]
        seat = ((rho > v["r_throat"] - 0.5) & (rho < v["r_head"] + 0.3) & (t > v["t_face"] - 1.0) & (t < v["t_inner"] + 1.5)
                & (n @ d < -0.2) & (np.einsum("ij,ij->i", n, radial) < 0.0))
        group[seat & (group == 0)] = GROUPS.index(f"seat_{v['role']}") + 1
        g0, g1 = v["guide_stations"]
        guide = (np.abs(rho - v["r_guide"]) < 0.6) & (t > g0 + 0.5) & (t < g1 - 0.5) & (np.einsum("ij,ij->i", n, radial) < -0.7)
        group[guide & (group == 0)] = GROUPS.index(f"guide_{v['role']}") + 1
    for name, p in comps["plugs"].items():
        d = np.asarray(p["direction"])
        t, rho = at.axis_coordinates(c, p["origin"], d)
        behind |= (rho < p["r_thread"] + 1.5) & (t > p["t_tip"] - 1.5)
        radial = (c - np.asarray(p["origin"]) - np.outer(t, d)) / np.maximum(rho, 1e-9)[:, None]
        thread = (np.abs(rho - p["r_thread"]) < 0.7) & (t > p["t_tip"]) & (t < p["t_seat"]) & (np.einsum("ij,ij->i", n, radial) < -0.7)
        group[thread & (group == 0)] = GROUPS.index(f"thread_{name}") + 1
    group[chamber & ~behind & (group == 0)] = GROUPS.index("chamber") + 1
    areas = {g: round(float(area[group == i + 1].sum()), 1) for i, g in enumerate(GROUPS)}
    return group, areas, seats, comps


def barycentric_field(points, nodes, tets, values):
    """Linear interpolation of a nodal field of a tetrahedral mesh; points outside every tet take the
    value of the nearest node. Returns (values, share of points outside)."""

    from scipy.spatial import cKDTree

    cen = nodes[tets].mean(axis=1)
    tree = cKDTree(cen)
    out = np.full(len(points), np.nan)
    _, cand = tree.query(points, k=12)
    for j in range(cand.shape[1]):
        todo = np.isnan(out)
        if not todo.any():
            break
        tt = tets[cand[todo, j]]
        p = nodes[tt]
        m = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]], axis=2)
        lam = np.linalg.solve(m, (points[todo] - p[:, 0])[:, :, None])[:, :, 0]
        bary = np.column_stack([1.0 - lam.sum(axis=1), lam])
        inside = (bary > -1e-6).all(axis=1)
        idx = np.flatnonzero(todo)[inside]
        out[idx] = (bary[inside] * values[tt[inside]]).sum(axis=1)
    miss = np.isnan(out)
    if miss.any():
        _, near = cKDTree(nodes).query(points[miss])
        out[miss] = values[near]
    return out, float(miss.mean())


def prepare_level(tets_npz, params, hp_work, thermal_dir, out_npz, report) -> None:
    """Load faces, holds and the temperature of every candidate field at the vertices of one mesh level."""

    import assembly_heat_paths as ahp

    d = np.load(tets_npz)
    xyz, tets = d["xyz"], d["tets"].astype(np.int64)
    faces = boundary_faces(tets)
    group, areas, seats, comps = classify_faces(xyz, faces, params)
    lc = load_case(params)
    hold = lc["holds"]
    r_mid = 0.5 * (hold["bore_radius_mm"]["value"] + hold["collar_radius_mm"]["value"])
    sup_nodes = np.unique(faces[group == GROUPS.index("support") + 1])
    pick = lambda q: int(sup_nodes[np.argmin(np.linalg.norm(xyz[sup_nodes] - np.asarray(q), axis=1))])
    z_floor = hold["register_floor_z_mm"]["value"]
    a_node, b_node = pick((r_mid, 0.0, z_floor)), pick((-r_mid, 0.0, z_floor))
    # temperatures: the heat-path field of each conductivity, interpolated in the head-alloy tetrahedra
    hp = np.load(Path(hp_work) / "prepared.npz", allow_pickle=False)
    split, material, source = hp["split"], hp["material"], hp["source"]
    hx = hp["xyz"][source]
    alloy_tets = split[material == ahp.MATERIALS.index("alloy")].astype(np.int64)
    fields, outside = {}, {}
    for folder in sorted(Path(thermal_dir).glob("k*")):
        f = np.load(folder / "alloy-field.npz")
        full = np.full(len(hx), np.nan)
        node_mat = np.full(len(hx), -1, dtype=np.int8)
        for i in range(len(ahp.MATERIALS)):
            node_mat[np.unique(split[material == i])] = i
        alloy = np.flatnonzero(node_mat == 0)
        assert np.allclose(hx[alloy], f["xyz"], atol=1e-3)
        full[alloy] = f["temperature_C"]
        # tets of the alloy whose nodes are all alloy nodes carry a field everywhere
        ok = ~np.isnan(full[alloy_tets]).any(axis=1)
        vals, miss = barycentric_field(xyz, hx, alloy_tets[ok], np.nan_to_num(full))
        fields[folder.name] = vals.astype(np.float32)
        outside[folder.name] = round(miss, 5)
    np.savez_compressed(out_npz, xyz=xyz, tets=tets.astype(np.int32), faces=faces.astype(np.int32), group=group,
                        hold_a=a_node, hold_b=b_node, **{f"T_{k}": v for k, v in fields.items()})
    rep = {"tets_npz": str(tets_npz), "vertices": int(len(xyz)), "tets": int(len(tets)), "boundary_faces": int(len(faces)),
           "group_area_mm2": areas, "studs": seats, "hold_vertices": {"a": xyz[a_node].round(3).tolist(), "b": xyz[b_node].round(3).tolist()},
           "fields": {k: {"min_C": round(float(v.min()), 2), "max_C": round(float(v.max()), 2), "mean_C": round(float(v.mean()), 2),
                          "share_of_vertices_outside_the_thermal_alloy": outside[k]} for k, v in fields.items()}}
    Path(report).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=1))


def solve_level(level_npz, params, out_npz, report) -> None:
    """Unit cases on one mesh level (DOLFINx, MPI): stud force, gas pressure, guide fits, each thermal field."""

    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    t0 = time.time()
    lc = load_case(params)
    data = None
    if comm.rank == 0:
        d = np.load(level_npz)
        data = {k: d[k] for k in d.files}
    meta = comm.bcast(None if data is None else {"hold_a": int(data["hold_a"]), "hold_b": int(data["hold_b"]),
                                                  "fields": sorted(k for k in data if k.startswith("T_"))}, root=0)
    xyz = data["xyz"] if data else None
    el = Elastic(xyz, data["tets"] if data else None, data["faces"] if data else None, data["group"] if data else None,
                 len(GROUPS), float(lc["material_model"]["poisson_ratio"]["value"]), log=lambda *a: None)
    gi = {g: i + 1 for i, g in enumerate(GROUPS)}
    el.fix(component_faces=[(2, gi["support"])], vertices=[(meta["hold_a"], (0, 1)), (meta["hold_b"], (1,))])
    el.factorise()
    # face areas and projections on rank 0, for the unit loads
    loads = None
    if comm.rank == 0:
        comps = components(params)
        c, n, area = face_geometry(data["xyz"], data["faces"])
        grp = data["group"]
        loads = {"stud": {}, "gas_p": {gi["chamber"]: 1.0}, "gas_q": {}}
        for s in STUDS:
            g = gi["nut_" + s[5:]]
            loads["stud"][g] = 1000.0 / float(area[grp == g].sum())         # 1 kN per stud, MPa on the seat
        for name, v in comps["valves"].items():
            g = gi[f"seat_{v['role']}"]
            sel = grp == g
            dvec = np.asarray(v["direction"])
            force = np.pi * v["r_seat"] ** 2                                # 1 MPa on the valve face inside the seat
            loads["gas_p"][g] = force / float((area[sel] * np.abs(n[sel] @ dvec)).sum())
        for name, p in comps["plugs"].items():
            g = gi[f"thread_{name}"]
            force = np.pi * p["r_thread"] ** 2
            loads["gas_q"][g] = (force / float(area[grp == g].sum()) * np.asarray(p["direction"])).tolist()
    loads = comm.bcast(loads, root=0)
    cases = [("stud_1kN_each", {"pressures": loads["stud"]}),
             ("gas_1MPa", {"pressures": loads["gas_p"], "tractions": loads["gas_q"]}),
             ("guide_fit_inlet_1MPa", {"pressures": {gi["guide_inlet"]: 1.0}}),
             ("guide_fit_exhaust_1MPa", {"pressures": {gi["guide_exhaust"]: 1.0}})]
    results, timing = {}, {}
    for label, kw in cases:
        s, rel = el.solve(**kw)
        results[label] = el.vertex_stress()
        timing[label] = {"solve_s": round(s, 2), "relative_residual": rel}
    for key in meta["fields"]:
        el.set_temperature(comm.bcast(data[key] if data else None, root=0))
        s, rel = el.solve(thermal=True)
        results[f"thermal_{key[2:]}"] = el.vertex_stress()
        timing[f"thermal_{key[2:]}"] = {"solve_s": round(s, 2), "relative_residual": rel}
    if comm.rank == 0:
        np.savez_compressed(out_npz, **{k: v.astype(np.float32) for k, v in results.items()})
        rep = {"level": str(level_npz), "processes": comm.size, "dofs": int(el.dofs), "factorise_s": round(el.factor_s, 1),
               "unit_loads": loads, "cases": timing, "wall_s": round(time.time() - t0, 1),
               "units": {"stud": "1 kN on each of the four nut seats", "gas": "1 MPa", "guide": "1 MPa on the bore",
                         "thermal": f"E {E_REF:g} MPa, alpha {ALPHA_REF:g} /K, from {T_REF:g} degC"}}
        Path(report).write_text(json.dumps(rep, indent=2) + "\n")
        print(json.dumps(rep, indent=1))


def kuhn_tets(nodes_shape):
    """Six tetrahedra per hexahedral cell of a structured (ni, nj, nk) node grid, all split along the same
    diagonal so that neighbouring cells conform. Node (i, j, k) has index (i * nj + j) * nk + k."""

    ni, nj, nk = nodes_shape
    idx = np.arange(ni * nj * nk).reshape(ni, nj, nk)
    corner = {}
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                corner[(a, b, c)] = idx[a:ni - 1 + a, b:nj - 1 + b, c:nk - 1 + c].ravel()
    tets = []
    for perm in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        path = [(0, 0, 0)]
        for axis in perm:
            step = list(path[-1])
            step[axis] = 1
            path.append(tuple(step))
        tets.append(np.stack([corner[q] for q in path], axis=1))
    return np.concatenate(tets)


def oriented(xyz, tets):
    p = xyz[tets]
    vol = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), p[:, 3] - p[:, 0])
    tets = tets.copy()
    tets[vol < 0] = tets[vol < 0][:, [0, 2, 1, 3]]
    return tets


def witness(out, size="1.0") -> None:
    """Closed forms for the solver path: a thick cylinder under pressure, its free expansion, a free block
    with a linear temperature. Run with mpirun; rank 0 writes OUT."""

    from mpi4py import MPI

    comm = MPI.COMM_WORLD
    h = float(size)
    nu = 0.33
    a, b, height, p = 10.0, 30.0, 10.0, 100.0
    rows = []

    xyz = tets = faces = groups = None
    if comm.rank == 0:
        # quarter ring on a structured polar grid: radial cells graded toward the bore, h at the bore
        nr, nt, nz = int(round(2.0 * (b - a) / h)), int(round(0.5 * np.pi * a / h * 2.0)), max(2, int(round(height / h)))
        rr = a + (b - a) * np.linspace(0.0, 1.0, nr + 1) ** 1.6
        th = np.linspace(0.0, 0.5 * np.pi, nt + 1)
        zz = np.linspace(0.0, height, nz + 1)
        R, TH, Z = np.meshgrid(rr, th, zz, indexing="ij")
        xyz = np.column_stack([(R * np.cos(TH)).ravel(), (R * np.sin(TH)).ravel(), Z.ravel()])
        tets = oriented(xyz, kuhn_tets(R.shape))
        faces = boundary_faces(tets)
        c, n, _ = face_geometry(xyz, faces)
        r = np.hypot(c[:, 0], c[:, 1])
        groups = np.full(len(faces), 6, dtype=np.int32)                      # outer
        groups[(r < a + 1e-6 + 0.01 * a) & (np.einsum("ij,ij->i", n[:, :2], c[:, :2]) < 0)] = 1   # bore
        groups[n[:, 0] < -0.99] = 2                                         # x = 0
        groups[n[:, 1] < -0.99] = 3                                         # y = 0
        groups[n[:, 2] < -0.99] = 4                                         # z = 0
        groups[n[:, 2] > 0.99] = 5                                          # z = h
    el = Elastic(xyz, tets, faces, groups, 6, nu, log=lambda *x: None)
    el.fix(component_faces=[(0, 2), (1, 3), (2, 4), (2, 5)])
    el.factorise()
    n_dofs = el.dofs
    s_case, rel = el.solve(pressures={1: p})
    sig = el.vertex_stress()
    bore_ids = None
    if comm.rank == 0:
        rr = np.hypot(xyz[:, 0], xyz[:, 1])
        bore_ids = np.flatnonzero((rr < a + 1e-6) & (xyz[:, 0] > 1.0) & (xyz[:, 1] > 1.0))
    bore_ids = comm.bcast(bore_ids, root=0)
    disp = el.displacement_at(bore_ids)
    if comm.rank == 0:
        A, B = p * a * a / (b * b - a * a), p * a * a * b * b / (b * b - a * a)
        x, y = xyz[bore_ids, 0], xyz[bore_ids, 1]
        cth, sth = x / np.hypot(x, y), y / np.hypot(x, y)
        s = sig[bore_ids]
        s_rr = s[:, 0] * cth ** 2 + s[:, 1] * sth ** 2 + 2 * s[:, 3] * cth * sth
        s_tt = s[:, 0] * sth ** 2 + s[:, 1] * cth ** 2 - 2 * s[:, 3] * cth * sth
        u_r = disp[:, 0] * cth + disp[:, 1] * sth
        u_exact = (1 + nu) / E_REF * ((1 - 2 * nu) * A * a + B / a)
        rows.append({"case": "thick cylinder, internal pressure, plane strain", "dofs": int(n_dofs),
                     "pressure_MPa": p, "radii_mm": [a, b],
                     "hoop_at_bore_MPa": {"expected": round(A + B / a ** 2, 3), "mean": round(float(s_tt.mean()), 3),
                                          "min": round(float(s_tt.min()), 3), "max": round(float(s_tt.max()), 3)},
                     "radial_at_bore_MPa": {"expected": -p, "mean": round(float(s_rr.mean()), 3)},
                     "axial_MPa": {"expected": round(2 * nu * A, 3), "mean": round(float(s[:, 2].mean()), 3)},
                     "radial_displacement_at_bore_mm": {"expected": round(u_exact, 6), "mean": round(float(u_r.mean()), 6)},
                     "relative_residual": float(rel)})
    # Free expansion of the same ring, held between its end planes: sigma_zz = -E alpha dT, nothing else.
    dT = 100.0
    el.set_temperature(np.full(el.n_nodes, T_REF + dT) if True else None)
    s_case, rel = el.solve(thermal=True)
    sig = el.vertex_stress()
    if comm.rank == 0:
        expected = -E_REF * ALPHA_REF * dT
        rows.append({"case": "uniform heating of the ring held between its end planes", "dT_K": dT,
                     "axial_MPa": {"expected": expected, "min": round(float(sig[:, 2].min()), 4), "max": round(float(sig[:, 2].max()), 4)},
                     "largest_other_component_MPa": round(float(np.abs(sig[:, [0, 1, 3, 4, 5]]).max()), 5),
                     "relative_residual": float(rel)})

    # A free block under a linear temperature: compatible strain, no stress. Held at three vertices (3-2-1).
    L, W, H = 20.0, 10.0, 10.0
    xyz = tets = faces = groups = None
    corners = None
    if comm.rank == 0:
        g = [np.linspace(0.0, d, max(2, int(round(d / h))) + 1) for d in (L, W, H)]
        X, Y, Z = np.meshgrid(*g, indexing="ij")
        xyz = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
        tets = oriented(xyz, kuhn_tets(X.shape))
        faces = boundary_faces(tets)
        groups = np.ones(len(faces), dtype=np.int32)
        corners = [int(np.argmin(np.linalg.norm(xyz - np.array(q), axis=1))) for q in ((0, 0, 0), (L, 0, 0), (0, W, 0))]
    corners = comm.bcast(corners, root=0)
    el = Elastic(xyz, tets, faces, groups, 1, nu, log=lambda *x: None)
    el.fix(vertices=[(corners[0], (0, 1, 2)), (corners[1], (1, 2)), (corners[2], (2,))])
    el.factorise()
    xs = comm.bcast(xyz[:, 0] if comm.rank == 0 else None, root=0)
    el.set_temperature(T_REF + 5.0 * xs + 2.0 * comm.bcast(xyz[:, 2] if comm.rank == 0 else None, root=0))
    s_case, rel = el.solve(thermal=True)
    sig = el.vertex_stress()
    if comm.rank == 0:
        rows.append({"case": "free block, temperature linear in x and z (20 to 140 K above reference)", "dofs": int(el.dofs),
                     "largest_von_mises_MPa": round(float(von_mises(sig).max()), 6),
                     "scale_E_alpha_dT_MPa": round(E_REF * ALPHA_REF * 120.0, 1), "relative_residual": float(rel)})
        Path(out).write_text(json.dumps({"schema": "935-cad-twin-head-stress-witness/1", "processes": comm.size,
                                         "mesh_size_mm": h, "element": "P2 tetrahedra on P1 geometry",
                                         "solver": "MUMPS Cholesky (PETSc), one factorisation, unit cases as right-hand sides",
                                         "rows": rows}, indent=2) + "\n")
        print(json.dumps(rows, indent=1))


def main(argv) -> None:
    commands = {"thermal": thermal, "solid": solid, "remesh": remesh, "tetmesh": tetmesh, "witness": witness,
                "prepare": prepare_level, "solve": solve_level}
    if len(argv) < 2 or argv[1] not in commands:
        raise SystemExit(__doc__)
    commands[argv[1]](*argv[2:])


if __name__ == "__main__":
    main(sys.argv)
