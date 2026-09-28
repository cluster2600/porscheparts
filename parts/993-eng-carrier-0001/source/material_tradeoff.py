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
import json
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
ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "twins" / "catalogue-parts" / "engine-carrier-material-screening-f1.json"


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


def build_report() -> dict:
    """Build a reproducible generic-material screening without part credit."""
    inertia = second_moment(HEIGHT_MM, WIDTH_MM, WALL_MM)
    area = section_area(HEIGHT_MM, WIDTH_MM, WALL_MM)
    steel = MATERIALS["steel"]
    ti = MATERIALS["ti64"]
    steel_ei = steel["E_MPa"] * inertia
    steel_mass = mass_kg(area, SPAN_MM, steel["rho_kg_m3"])
    ti_mass_same_geometry = mass_kg(area, SPAN_MM, ti["rho_kg_m3"])
    steel_deflection = tip_deflection_mm(
        TIP_LOAD_N, SPAN_MM, steel["E_MPa"], inertia
    )
    ti_deflection = tip_deflection_mm(
        TIP_LOAD_N, SPAN_MM, ti["E_MPa"], inertia
    )
    stiffness_scale = scale_for_equal_stiffness(steel_ei, ti["E_MPa"])
    equal_stiffness_area = section_area(
        HEIGHT_MM * stiffness_scale,
        WIDTH_MM * stiffness_scale,
        WALL_MM * stiffness_scale,
    )
    ti_mass_equal_stiffness = mass_kg(
        equal_stiffness_area, SPAN_MM, ti["rho_kg_m3"]
    )
    equal_mass_scale = (steel["rho_kg_m3"] / ti["rho_kg_m3"]) ** 0.5
    equal_mass_inertia = second_moment(
        HEIGHT_MM * equal_mass_scale,
        WIDTH_MM * equal_mass_scale,
        WALL_MM * equal_mass_scale,
    )
    return {
        "$comment": (
            "Screening analytique d'un coupon generique, pas calcul du berceau. "
            "Aucune valeur de contrainte, fatigue, tenue ou fabrication n'est deduite."
        ),
        "schema_version": "1.0.0",
        "generated_by": str(Path(__file__).resolve().relative_to(ROOT)),
        "subject": {
            "part_id": "993-ENG-CARRIER-0001",
            "oem_reference": "993 115 021 53",
            "scope": "generic_rectangular_tube_material_tradeoff_only",
            "component_geometry_used": False,
        },
        "status": "F1_generic_analytic_screening_complete_no_component_credit",
        "coupon": {
            "span_mm": SPAN_MM,
            "height_mm": HEIGHT_MM,
            "width_mm": WIDTH_MM,
            "wall_mm": WALL_MM,
            "tip_load_N": TIP_LOAD_N,
            "area_mm2": round(area, 6),
            "second_moment_mm4": round(inertia, 6),
            "boundary_condition": "ideal_cantilever_tip_load",
        },
        "material_hypotheses": {
            name: {
                "elastic_modulus_MPa": props["E_MPa"],
                "density_kg_m3": props["rho_kg_m3"],
                "poisson_ratio": props["nu"],
                "qualification_status": "generic_handbook_value_not_supplier_qualified",
            }
            for name, props in MATERIALS.items()
        },
        "analytic_results": {
            "same_geometry": {
                "steel_mass_kg": round(steel_mass, 9),
                "ti64_mass_kg": round(ti_mass_same_geometry, 9),
                "steel_tip_deflection_mm": round(steel_deflection, 9),
                "ti64_tip_deflection_mm": round(ti_deflection, 9),
                "ti64_mass_reduction_fraction": round(
                    1.0 - ti_mass_same_geometry / steel_mass, 9
                ),
                "ti64_deflection_ratio": round(ti_deflection / steel_deflection, 9),
            },
            "same_bending_stiffness": {
                "ti64_uniform_section_scale": round(stiffness_scale, 9),
                "ti64_mass_kg": round(ti_mass_equal_stiffness, 9),
                "steel_mass_kg": round(steel_mass, 9),
                "ti64_mass_reduction_fraction": round(
                    1.0 - ti_mass_equal_stiffness / steel_mass, 9
                ),
            },
            "same_mass": {
                "ti64_uniform_section_scale": round(equal_mass_scale, 9),
                "ti64_to_steel_bending_stiffness_ratio": round(
                    ti["E_MPa"] * equal_mass_inertia / steel_ei, 9
                ),
            },
            "material_index_sqrt_E_over_density": {
                name: round((props["E_MPa"] ** 0.5) / props["rho_kg_m3"] * 1000, 9)
                for name, props in MATERIALS.items()
            },
        },
        "model_verification": {
            "analytic_equations_executed": True,
            "independent_component_FEA": "not_run_missing_component_geometry",
            "generic_coupon_CalculiX_crosscheck": "optional_not_release_evidence",
            "component_model_verified": False,
        },
        "screening_decision": {
            "titanium_route": "deprioritized_for_current_concept_program",
            "reason": (
                "generic stiffness screening and the declared 1.96 kg component mass "
                "do not justify a titanium redevelopment before geometry and loads"
            ),
            "machined_wrought_steel_route": "candidate_pending_geometry_loads_grade_and_fatigue_review",
            "selected_material": None,
            "selected_functional_process": None,
            "component_credit": False,
        },
        "downstream_models": {
            "reference_solver": "CalculiX_after_F3_geometry_and_boundary_completion",
            "physicsnemo": "blocked_until_validated_reference_CAE_dataset_exists",
            "omniverse": "F1_envelope_visualization_only_not_SimReady",
        },
        "release_gates": {
            "dimensionally_accurate": False,
            "fitment_validated": False,
            "material_qualified": False,
            "reference_CAE_passed": False,
            "physicsnemo_validated": False,
            "simready_validated": False,
            "manufacturing": False,
            "installation": False,
            "road_use": False,
        },
    }


def render_report(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="write the tracked JSON screening report")
    mode.add_argument("--check", action="store_true", help="check the tracked JSON screening report")
    args = parser.parse_args(argv)

    report_text = render_report(build_report())
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(report_text, encoding="utf-8")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
    elif args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != report_text:
            print(f"stale:{OUTPUT}")
            return 1
        print(f"current {OUTPUT.relative_to(ROOT)}")
    if (args.write or args.check) and not args.fea:
        return 0

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
