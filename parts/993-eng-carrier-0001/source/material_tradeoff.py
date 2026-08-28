#!/usr/bin/env python3
"""Steel versus Ti-6Al-4V on a bending member: does titanium actually save mass?

This studies a generic rectangular tube, NOT the 993 engine carrier: its real
section, span and load path are unknown and cannot be obtained from public data.
The question it answers is the one that decides whether the titanium route is
worth pursuing at all.

Three comparisons:
  A  same geometry           -> how much stiffness is lost with titanium
  B  same bending stiffness  -> how much section growth titanium needs, and
                                whether mass still falls after that growth
  C  same mass               -> which material is stiffer for the mass

Analytic results are cross-checked with a CalculiX cantilever.

  python parts/993-eng-carrier-0001/source/material_tradeoff.py [--fea]

Elastic constants are generic handbook values for a wrought steel and for
Ti-6Al-4V. An LPBF part must use the supplier's qualified values instead; see
docs/TITANIUM.md.
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

MATERIALS = {
    "steel": {"E_MPa": 210_000.0, "rho_kg_m3": 7850.0, "nu": 0.30},
    "ti64": {"E_MPa": 114_000.0, "rho_kg_m3": 4430.0, "nu": 0.34},
}

# Study coupon: rectangular tube, bending about the tall axis.
SPAN_MM = 600.0
HEIGHT_MM = 60.0
WIDTH_MM = 40.0
WALL_MM = 3.0
TIP_LOAD_N = 1000.0


def second_moment(height: float, width: float, wall: float) -> float:
    outer = width * height ** 3 / 12.0
    inner = (width - 2 * wall) * (height - 2 * wall) ** 3 / 12.0
    return outer - inner


def section_area(height: float, width: float, wall: float) -> float:
    return width * height - (width - 2 * wall) * (height - 2 * wall)


def mass_kg(area_mm2: float, span_mm: float, rho_kg_m3: float) -> float:
    return area_mm2 * span_mm * 1e-9 * rho_kg_m3


def tip_deflection_mm(load_N: float, span_mm: float, E_MPa: float, inertia_mm4: float) -> float:
    return load_N * span_mm ** 3 / (3.0 * E_MPa * inertia_mm4)


def scale_for_equal_stiffness(target_EI: float, E_MPa: float) -> float:
    """Uniform scale factor on the section that restores the target EI."""
    low, high = 0.5, 4.0
    for _ in range(200):
        mid = (low + high) / 2
        inertia = second_moment(HEIGHT_MM * mid, WIDTH_MM * mid, WALL_MM * mid)
        if E_MPa * inertia < target_EI:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def fea_tip_deflection(E_MPa: float, nu: float) -> float:
    """Cantilever check with gmsh and CalculiX, same section and load."""
    import gmsh

    work = Path(tempfile.mkdtemp(prefix="tradeoff-"))
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    outer = gmsh.model.occ.addBox(0, -WIDTH_MM / 2, -HEIGHT_MM / 2, SPAN_MM, WIDTH_MM, HEIGHT_MM)
    inner = gmsh.model.occ.addBox(
        0, -(WIDTH_MM / 2 - WALL_MM), -(HEIGHT_MM / 2 - WALL_MM),
        SPAN_MM, WIDTH_MM - 2 * WALL_MM, HEIGHT_MM - 2 * WALL_MM,
    )
    gmsh.model.occ.cut([(3, outer)], [(3, inner)])
    gmsh.model.occ.synchronize()
    volumes = [tag for _, tag in gmsh.model.getEntities(3)]
    gmsh.model.addPhysicalGroup(3, volumes, name="BODY")
    gmsh.option.setNumber("Mesh.MeshSizeMax", 8.0)
    gmsh.option.setNumber("Mesh.ElementOrder", 2)
    gmsh.option.setNumber("Mesh.SaveAll", 0)
    gmsh.model.mesh.generate(3)
    tags, coords, _ = gmsh.model.mesh.getNodes()
    gmsh.write(str(work / "mesh.inp"))
    gmsh.finalize()

    points = {int(t): coords[3 * i:3 * i + 3] for i, t in enumerate(tags)}
    fixed = sorted(n for n, p in points.items() if p[0] < 1e-6)
    loaded = sorted(n for n, p in points.items() if p[0] > SPAN_MM - 1e-6)

    def nset(name, nodes):
        rows = [", ".join(str(n) for n in nodes[i:i + 8]) for i in range(0, len(nodes), 8)]
        return f"*NSET, NSET={name}\n" + "\n".join(rows) + "\n"

    deck = (
        "*INCLUDE, INPUT=mesh.inp\n"
        + nset("FIXED", fixed)
        + nset("TIP", loaded)
        + f"*MATERIAL, NAME=MAT\n*ELASTIC\n{E_MPa}, {nu}\n"
        + "*SOLID SECTION, ELSET=BODY, MATERIAL=MAT\n"
        + "*STEP\n*STATIC\n*BOUNDARY\nFIXED, 1, 3\n"
        + f"*CLOAD\nTIP, 3, {-TIP_LOAD_N / len(loaded):.8f}\n"
        + "*NODE PRINT, NSET=TIP\nU\n*END STEP\n"
    )
    (work / "solve.inp").write_text(deck)
    subprocess.run(["ccx", "-i", "solve"], cwd=work, capture_output=True, text=True, check=True)

    uz = []
    for line in (work / "solve.dat").read_text().splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0].isdigit():
            uz.append(float(parts[3]))
    return abs(min(uz))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fea", action="store_true", help="cross-check the analytic result with CalculiX")
    args = parser.parse_args(argv)

    inertia = second_moment(HEIGHT_MM, WIDTH_MM, WALL_MM)
    area = section_area(HEIGHT_MM, WIDTH_MM, WALL_MM)
    print(f"Study coupon: rectangular tube {WIDTH_MM} x {HEIGHT_MM} x {WALL_MM} mm wall, span {SPAN_MM} mm")
    print(f"  I = {inertia:.0f} mm4, A = {area:.0f} mm2, tip load {TIP_LOAD_N:.0f} N\n")

    steel, ti = MATERIALS["steel"], MATERIALS["ti64"]
    steel_EI = steel["E_MPa"] * inertia
    steel_mass = mass_kg(area, SPAN_MM, steel["rho_kg_m3"])
    ti_mass_same_geom = mass_kg(area, SPAN_MM, ti["rho_kg_m3"])

    print("A. Same geometry")
    d_steel = tip_deflection_mm(TIP_LOAD_N, SPAN_MM, steel["E_MPa"], inertia)
    d_ti = tip_deflection_mm(TIP_LOAD_N, SPAN_MM, ti["E_MPa"], inertia)
    print(f"   steel: {steel_mass * 1000:.0f} g, tip deflection {d_steel:.3f} mm")
    print(f"   ti64 : {ti_mass_same_geom * 1000:.0f} g, tip deflection {d_ti:.3f} mm")
    print(f"   -> {(1 - ti_mass_same_geom / steel_mass) * 100:.0f}% lighter but {d_ti / d_steel:.2f}x more flexible\n")

    print("B. Same bending stiffness")
    scale = scale_for_equal_stiffness(steel_EI, ti["E_MPa"])
    h2, w2, t2 = HEIGHT_MM * scale, WIDTH_MM * scale, WALL_MM * scale
    area2 = section_area(h2, w2, t2)
    ti_mass_equal = mass_kg(area2, SPAN_MM, ti["rho_kg_m3"])
    print(f"   titanium section must grow by {scale:.3f}x -> {w2:.1f} x {h2:.1f} mm, wall {t2:.2f} mm")
    print(f"   ti64 mass {ti_mass_equal * 1000:.0f} g versus steel {steel_mass * 1000:.0f} g")
    delta = (1 - ti_mass_equal / steel_mass) * 100
    verdict = f"{delta:.0f}% lighter" if delta > 0 else f"{-delta:.0f}% heavier"
    print(f"   -> at equal stiffness: {verdict}, but the part is {(scale - 1) * 100:.0f}% bigger\n")

    print("C. Same mass")
    mass_scale = (steel["rho_kg_m3"] / ti["rho_kg_m3"]) ** 0.5
    h3, w3, t3 = HEIGHT_MM * mass_scale, WIDTH_MM * mass_scale, WALL_MM * mass_scale
    inertia3 = second_moment(h3, w3, t3)
    print(f"   titanium section at equal mass: {w3:.1f} x {h3:.1f} mm, wall {t3:.2f} mm")
    print(f"   EI ratio titanium/steel = {ti['E_MPa'] * inertia3 / steel_EI:.2f}\n")

    print("Material index for a bending member free to grow, E^0.5/rho (higher is better):")
    for name, props in MATERIALS.items():
        print(f"   {name:6s} {(props['E_MPa'] ** 0.5) / props['rho_kg_m3'] * 1000:.3f}")

    if args.fea:
        print("\nFEA cross-check (CalculiX, quadratic tetrahedra):")
        for name, props in MATERIALS.items():
            computed = fea_tip_deflection(props["E_MPa"], props["nu"])
            analytic = tip_deflection_mm(TIP_LOAD_N, SPAN_MM, props["E_MPa"], inertia)
            print(f"   {name:6s} FEA {computed:.3f} mm vs beam theory {analytic:.3f} mm "
                  f"({(computed / analytic - 1) * 100:+.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
