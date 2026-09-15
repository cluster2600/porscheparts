#!/usr/bin/env python3
"""Criblages FEA CalculiX des composants acceptes par les agents.

- modal : vilebrequin (ou toute piece), modes propres libre-libre ;
- static : bielle (ou toute piece), encastrement d'une zone, force sur une autre.
Unites : mm, t, s, N, MPa. Maillage Gmsh C3D10, deux tailles pour l'ecart de
convergence. Materiaux : cartes de criblage, jamais une propriete qualifiee.
Chaque sortie reste screen_unreviewed : ni validation, ni autorisation.

--self-check compare une poutre cylindrique a Euler-Bernoulli (flexion
libre-libre et console), pour prouver la chaine avant tout usage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

MATERIALS = {
    # Acier trempe-revenu type 42CrMo4 : ordre de grandeur de manuel, hypothese.
    "steel_42crmo4_hypothesis": {"E_mpa": 210000.0, "nu": 0.30, "rho_t_mm3": 7.85e-9, "source_type": "estimated"},
    # Ti-6Al-4V : bas de plage E a 20 C et densite de twins/engine-simulation-contracts/materials-f1.json.
    "ti64_materials_f1": {"E_mpa": 107000.0, "nu": 0.31, "rho_t_mm3": 4.43e-9,
                          "source_type": "documented", "source": "materials-f1.json#ti64_grade5_eos_lpbf_candidate"},
}
GROUND_SPRING_HZ = 0.5
MIN_ELASTIC_HZ = 5.0
C3D10_ORDER =[0, 1, 2, 3, 4, 5, 6, 7, 9, 8]  # Gmsh -> CalculiX, milieux 2-4 et 3-4


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(step: Path, size: float):
    import gmsh

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.merge(str(step))
        if len(gmsh.model.getEntities(3)) != 1:
            raise RuntimeError(f"expected_one_volume:{len(gmsh.model.getEntities(3))}")
        gmsh.option.setNumber("Mesh.MeshSizeMin", size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)
        gmsh.model.mesh.generate(3)
        tags, coords, _ = gmsh.model.mesh.getNodes()
        points = {int(t): tuple(float(c) for c in coords[3 * i:3 * i + 3]) for i, t in enumerate(tags)}
        elements = []
        for etype, etags, enodes in zip(*gmsh.model.mesh.getElements(3)):
            if int(etype) != 11:
                continue
            for i, tag in enumerate(etags):
                nodes = [int(n) for n in enodes[10 * i:10 * i + 10]]
                elements.append((int(tag), [nodes[k] for k in C3D10_ORDER]))
    finally:
        gmsh.finalize()
    if not elements:
        raise RuntimeError("no_quadratic_tetrahedra")
    return points, elements


def write_mesh(stream, points, elements, material):
    stream.write("*NODE\n")
    for tag in sorted(points):
        x, y, z = points[tag]
        stream.write(f"{tag},{x:.9g},{y:.9g},{z:.9g}\n")
    stream.write("*ELEMENT,TYPE=C3D10,ELSET=BODY\n")
    for tag, nodes in elements:
        stream.write(f"{tag}," + ",".join(map(str, nodes)) + "\n")
    stream.write(f"*MATERIAL,NAME=M\n*ELASTIC\n{material['E_mpa']:.9g},{material['nu']:.9g}\n"
                 f"*DENSITY\n{material['rho_t_mm3']:.9g}\n*SOLID SECTION,ELSET=BODY,MATERIAL=M\n")


def write_set(stream, name, values):
    stream.write(f"*NSET,NSET={name}\n")
    for i in range(0, len(values), 16):
        stream.write(",".join(map(str, values[i:i + 16])) + "\n")


def nodes_in_slab(points, axis, lo, hi):
    return sorted(t for t, p in points.items() if lo <= p[axis] <= hi)


def run_ccx(case: Path, name: str, threads: int):
    proc = subprocess.run(["ccx", "-i", name], cwd=case, capture_output=True, text=True, timeout=3600,
                          env={"OMP_NUM_THREADS": str(threads), "CCX_NPROC_EQUATION_SOLVER": str(threads),
                               "PATH": "/usr/bin:/bin:/usr/local/bin"})
    dat = case / f"{name}.dat"
    if proc.returncode or not dat.exists():
        raise RuntimeError(f"ccx_failed:{proc.returncode}:{proc.stdout[-500:]}")
    return dat.read_text(errors="replace")


def parse_frequencies(dat: str):
    block = dat.split("E I G E N V A L U E   O U T P U T", 1)
    if len(block) < 2:
        raise RuntimeError("no_eigenvalue_output")
    freqs = []
    for line in block[1].splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[0].isdigit():
            freqs.append(float(fields[3]))
        elif freqs and not line.strip():
            break
    return freqs


def parse_static(dat: str):
    disp, vm, mode = [], [], None
    for line in dat.splitlines():
        low = line.lower()
        if "displacements" in low:
            mode = "u"
            continue
        if "stresses" in low:
            mode = "s"
            continue
        f = line.split()
        try:
            if mode == "u" and len(f) >= 4:
                int(f[0])
                disp.append(math.sqrt(sum(float(v) ** 2 for v in f[1:4])))
            elif mode == "s" and len(f) >= 8:
                int(f[0]); int(f[1])
                sxx, syy, szz, sxy, sxz, syz = map(float, f[2:8])
                vm.append(math.sqrt(0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                                    + 3 * (sxy ** 2 + sxz ** 2 + syz ** 2)))
        except ValueError:
            continue
    if not disp or not vm:
        raise RuntimeError("missing_static_results")
    vm.sort()
    return {"max_displacement_mm": max(disp), "von_mises_p99_mpa": vm[int(0.99 * (len(vm) - 1))],
            "von_mises_max_mpa": vm[-1]}


def tet_volume(points, nodes):
    a, b, c, d = (points[n] for n in nodes[:4])
    u, v, w = ([q[i] - a[i] for i in range(3)] for q in (b, c, d))
    return abs(u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0])
               + u[2] * (v[0] * w[1] - v[1] * w[0])) / 6.0


def write_ground_springs(stream, points, elements, material):
    """Ressorts tres souples vers le sol : les 6 modes rigides passent vers GROUND_SPRING_HZ.

    Le libre-libre pur rend des modes rigides mal separes (valeurs quasi nulles
    en surnombre, parasites a quelques Hz). L'influence sur un mode elastique f
    est de l'ordre de (GROUND_SPRING_HZ / f)^2.
    """
    mass = material["rho_t_mm3"] * sum(tet_volume(points, n) for _, n in elements)
    k = mass / len(points) * (2 * math.pi * GROUND_SPRING_HZ) ** 2
    first = max(tag for tag, _ in elements) + 1
    for dof in (1, 2, 3):
        stream.write(f"*ELEMENT,TYPE=SPRING1,ELSET=GROUND{dof}\n")
        for i, tag in enumerate(sorted(points)):
            stream.write(f"{first + (dof - 1) * len(points) + i},{tag}\n")
        stream.write(f"*SPRING,ELSET=GROUND{dof}\n{dof}\n{k:.9g}\n")
    return mass


def modal(step, case, size, material, modes, threads):
    points, elements = mesh(step, size)
    case.mkdir(parents=True, exist_ok=True)
    with (case / "modal.inp").open("w") as s:
        write_mesh(s, points, elements, material)
        mass = write_ground_springs(s, points, elements, material)
        s.write(f"*STEP\n*FREQUENCY,STORAGE=NO\n{modes + 6}\n*END STEP\n")
    freqs = parse_frequencies(run_ccx(case, "modal", threads))
    rigid = [f for f in freqs if f <= MIN_ELASTIC_HZ]
    elastic = [f for f in freqs if f > MIN_ELASTIC_HZ]
    if len(rigid) != 6 or not elastic:
        raise RuntimeError(f"rigid_mode_separation_failed:{len(rigid)}:{len(elastic)}")
    return {"nodes": len(points), "elements": len(elements), "mass_kg": mass * 1000.0,
            "rigid_frequencies_hz": rigid, "elastic_frequencies_hz": elastic[:modes]}


def static(step, case, size, material, axis, fix, load, force_n, force_dir, threads):
    points, elements = mesh(step, size)
    fixed, loaded = nodes_in_slab(points, axis, *fix), nodes_in_slab(points, axis, *load)
    if len(fixed) < 6 or len(loaded) < 4:
        raise RuntimeError(f"insufficient_boundary_nodes:{len(fixed)}:{len(loaded)}")
    case.mkdir(parents=True, exist_ok=True)
    with (case / "static.inp").open("w") as s:
        write_mesh(s, points, elements, material)
        write_set(s, "FIX", fixed)
        write_set(s, "LOAD", loaded)
        write_set(s, "NALL", sorted(points))
        s.write("*STEP\n*STATIC\n*BOUNDARY\nFIX,1,3\n*CLOAD\n")
        per = force_n / len(loaded)
        for t in loaded:
            s.write(f"{t},{force_dir + 1},{per:.9g}\n")
        s.write("*NODE PRINT,NSET=NALL\nU\n*EL PRINT,ELSET=BODY\nS\n*END STEP\n")
    return {"nodes": len(points), "elements": len(elements), "fixed_nodes": len(fixed),
            "loaded_nodes": len(loaded), **parse_static(run_ccx(case, "static", threads))}


def convergence(results, key):
    a, b = results
    if key == "elastic_frequencies_hz":
        n = min(len(a[key]), len(b[key]))
        return max(abs(a[key][i] - b[key][i]) / b[key][i] for i in range(n)) if n else None
    return abs(a[key] - b[key]) / b[key]


def self_check(out: Path, threads: int):
    import cadquery as cq

    L, r = 400.0, 10.0
    mat = MATERIALS["steel_42crmo4_hypothesis"]
    step = out / "beam.step"
    out.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(cq.Workplane("YZ").circle(r).extrude(L), str(step))
    I, A = math.pi * r ** 4 / 4, math.pi * r ** 2
    f1 = 4.730 ** 2 / (2 * math.pi * L ** 2) * math.sqrt(mat["E_mpa"] * I / (mat["rho_t_mm3"] * A))
    m = modal(step, out / "modal", 4.0, mat, 4, threads)
    P = 100.0
    s = static(step, out / "static", 4.0, mat, 0, (-0.01, 0.01), (L - 0.01, L + 0.01), P, 1, threads)
    tip = P * L ** 3 / (3 * mat["E_mpa"] * I)
    err_f = abs(m["elastic_frequencies_hz"][0] - f1) / f1
    err_u = abs(s["max_displacement_mm"] - tip) / tip
    report = {"analytic_f1_hz": f1, "fea_f1_hz": m["elastic_frequencies_hz"][0], "rel_error_f1": err_f,
              "analytic_tip_mm": tip, "fea_tip_mm": s["max_displacement_mm"], "rel_error_tip": err_u,
              "passed": err_f < 0.03 and err_u < 0.05}
    (out / "self-check.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--kind", choices=["modal", "static"])
    ap.add_argument("--step", type=Path)
    ap.add_argument("--component")
    ap.add_argument("--material", choices=sorted(MATERIALS))
    ap.add_argument("--mesh-sizes", type=float, nargs=2, default=[6.0, 4.0])
    ap.add_argument("--modes", type=int, default=6)
    ap.add_argument("--axis", type=int, choices=[0, 1, 2], help="static : axe des tranches d'appui et de charge")
    ap.add_argument("--fix", type=float, nargs=2, help="static : tranche encastree [min max] mm")
    ap.add_argument("--load", type=float, nargs=2, help="static : tranche chargee [min max] mm")
    ap.add_argument("--force-n", type=float, help="static : force totale, hypothese declaree")
    ap.add_argument("--force-dir", type=int, choices=[0, 1, 2])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()
    if args.self_check:
        report = self_check(args.out, args.threads)
        print(json.dumps(report))
        raise SystemExit(0 if report["passed"] else 1)
    if not (args.kind and args.step and args.component and args.material):
        ap.error("--kind, --step, --component et --material sont requis")
    if not re.fullmatch(r"[a-z0-9_]+", args.component):
        ap.error("identifiant de composant invalide")
    mat = MATERIALS[args.material]
    runs = []
    for size in args.mesh_sizes:
        case = args.out / f"{args.kind}-h{size:g}"
        if args.kind == "modal":
            runs.append({"mesh_size_mm": size, **modal(args.step, case, size, mat, args.modes, args.threads)})
        else:
            if None in (args.axis, args.fix, args.load, args.force_n, args.force_dir):
                ap.error("static exige --axis --fix --load --force-n --force-dir")
            runs.append({"mesh_size_mm": size, **static(args.step, case, size, mat, args.axis, args.fix, args.load,
                                                        args.force_n, args.force_dir, args.threads)})
    key = "elastic_frequencies_hz" if args.kind == "modal" else "von_mises_p99_mpa"
    report = {"component": args.component, "kind": args.kind, "status": "screen_unreviewed",
              "step_sha256": sha256(args.step), "material": {"id": args.material, **mat},
              "runs": runs, "mesh_relative_change": convergence(runs, key),
              "limits": "Carte de criblage, conditions aux limites simplifiees, geometrie d'agent non revue."}
    if args.kind == "static":
        report["load_hypothesis"] = {"force_n": args.force_n, "direction": args.force_dir, "source_type": "estimated"}
    (args.out / "fea-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({"component": args.component, "mesh_relative_change": report["mesh_relative_change"]}))


if __name__ == "__main__":
    main()
