#!/usr/bin/env python3
"""Compile le plan LPBF F37 à partir de son écran géométrique et du proxy mécanique F36.

La sortie est un dossier de fabrication virtuel, pas une autorisation d'imprimer.
Elle conserve séparément les résultats calculés, les hypothèses de procédé et
les contrôles physiques qui restent obligatoires.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--printability", type=Path, required=True)
    parser.add_argument("--f37-head-mesh-report", type=Path, required=True)
    parser.add_argument("--locked-plate", type=Path, required=True)
    parser.add_argument("--f37-contract", type=Path, required=True)
    parser.add_argument("--f37-cad-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def compact_orientation(entry: dict) -> dict:
    return {
        "id": entry["id"],
        "score": entry["score"],
        "extents_mm_if_scale_is_mm": entry["extents_mm_if_scale_is_mm"],
        "layer_count_at_50_um": entry["layer_count_at_50_um"],
        "downward_overhang_area_mm2": entry["downward_overhang_area_mm2"],
        "projected_support_area_mm2": entry["projected_support_area_mm2"],
        "column_support_volume_proxy_mm3": entry["column_support_volume_proxy_mm3"],
        "fits_250x250x325_mm": entry["fits_250x250x325_mm"],
    }


def validate_inputs(
    printability: dict,
    head_mesh: dict,
    locked: dict,
    contract: dict,
    cad: dict,
    args: argparse.Namespace,
) -> None:
    """Refuse tout assemblage ambigu, obsolète ou déjà présenté comme libéré."""

    if (
        printability.get("phase") != "F37"
        or head_mesh.get("phase") != "F37"
        or contract.get("phase") != "F37"
        or cad.get("phase") != "F37"
    ):
        raise ValueError("phases F37 inattendues")
    if printability.get("status") != "lpbf_geometric_virtual_build_screen_complete_release_blocked":
        raise ValueError("statut du criblage LPBF F37 inattendu")
    if printability.get("classification") != "virtual_printability_screen_not_calibrated_process_simulation":
        raise ValueError("classification du criblage LPBF F37 inattendue")
    if printability.get("voxel_audit", {}).get("method") != (
        "surface_voxel_components_plus_chunked_winding_number_without_fill_holes"
    ):
        raise ValueError("méthode d'audit voxel F37 inattendue")
    if head_mesh.get("status") != "local_mesh_boolean_proof_complete_physical_and_manufacturing_release_blocked":
        raise ValueError("statut du maillage F37 inattendu")
    if locked.get("phase") != "F36":
        raise ValueError("le calcul plaque bloquée doit rester explicitement un proxy F36")
    if locked.get("classification") != (
        "linear_elastic_uniform_cooling_locked_plate_upper_bound_not_calibrated_lpbf"
    ):
        raise ValueError("classification du calcul plaque bloquée inattendue")

    print_gates = printability.get("gates", {})
    for gate in ("metal_print_authorized", "engine_start_authorized"):
        if print_gates.get(gate) is not False:
            raise ValueError(f"le criblage LPBF doit conserver {gate}=false")
    for source_name, source in (("contrat", contract), ("CAO", cad)):
        release = source.get("release_gates", {})
        for gate in ("metal_print_authorized", "engine_start_authorized"):
            if release.get(gate) is not False:
                raise ValueError(f"{source_name}: la porte {gate} doit rester false")
    if cad.get("release_gates") != contract.get("release_gates"):
        raise ValueError("les portes de libération CAO ne correspondent pas au contrat F37")

    expected_head_sha = head_mesh["local_only_artifacts"][
        "917-head-f37-printable-proof.local.stl"
    ]["sha256"]
    if printability["inputs"]["head_sha256"] != expected_head_sha:
        raise ValueError("le test LPBF ne référence pas le maillage F37 exact")
    if printability["inputs"]["geometry_report_sha256"] != head_mesh["inputs"][
        "geometry_report_sha256"
    ]:
        raise ValueError("le test LPBF et le maillage F37 ne référencent pas la même géométrie parent")
    if bool(printability["inputs"]["scale_confirmed"]) != bool(
        head_mesh["inputs"]["scale_confirmed"]
    ):
        raise ValueError("état de confirmation d'échelle incohérent entre les preuves F37")
    if bool(print_gates.get("absolute_scale_confirmed")) != bool(
        printability["inputs"]["scale_confirmed"]
    ):
        raise ValueError("porte d'échelle LPBF incohérente avec son entrée métrologique")
    if head_mesh["inputs"]["contract_sha256"] != sha256(args.f37_contract):
        raise ValueError("le rapport de maillage F37 ne référence pas le contrat courant")
    if cad["inputs"]["contract_sha256"] != sha256(args.f37_contract):
        raise ValueError("le rapport CAO F37 ne référence pas le contrat courant")
    if head_mesh["inputs"]["cad_report_sha256"] != sha256(args.f37_cad_report):
        raise ValueError("le rapport de maillage F37 ne référence pas le rapport CAO courant")

    orientations = printability.get("orientations", [])
    eligible = [item for item in orientations if item.get("fits_250x250x325_mm") is True]
    if not eligible:
        raise ValueError("aucune orientation LPBF F37 admissible n'est enregistrée")
    expected_selected = min(eligible, key=lambda item: float(item["score"]))
    selected = printability.get("selected", {})
    if (
        printability.get("selected_orientation") != expected_selected.get("id")
        or selected.get("id") != expected_selected.get("id")
        or not math.isclose(float(selected.get("score", math.nan)), float(expected_selected["score"]), rel_tol=1e-12)
    ):
        raise ValueError("l'orientation retenue n'est pas le minimum admissible enregistré")
    if selected != expected_selected:
        raise ValueError("les métriques de l'orientation retenue diffèrent de l'entrée enregistrée")

    voxel = printability["voxel_audit"]
    pitch = float(voxel["pitch_mm"])
    trapped_count = int(voxel["trapped_void_voxels"])
    trapped_volume = float(voxel["trapped_void_volume_mm3"])
    unsupported_fraction = float(voxel["unsupported_fraction"])
    unsupported_count = int(voxel["unsupported_voxels_above_plate"])
    occupied_above_plate = int(voxel["occupied_voxels_above_plate"])
    if pitch <= 0.0 or trapped_count < 0 or not math.isclose(
        trapped_volume, trapped_count * pitch**3, rel_tol=1e-12, abs_tol=1e-9
    ):
        raise ValueError("arithmétique du volume de vide voxel incohérente")
    if not math.isfinite(unsupported_fraction) or not 0.0 <= unsupported_fraction <= 1.0:
        raise ValueError("fraction de matière sans appui hors domaine")
    expected_unsupported_fraction = unsupported_count / max(1, occupied_above_plate)
    if unsupported_count < 0 or occupied_above_plate < 0 or not math.isclose(
        unsupported_fraction, expected_unsupported_fraction, rel_tol=1e-12, abs_tol=1e-15
    ):
        raise ValueError("arithmétique de la fraction sans appui incohérente")
    if float(printability["head_mass_kg"]) <= 0.0:
        raise ValueError("masse LPBF non positive")
    assumed_density = float(printability["assumed_density_kg_m3"])
    if not math.isfinite(assumed_density) or assumed_density <= 0.0:
        raise ValueError("densité LPBF supposée non positive")

    thickness = printability["thickness_audit"]
    if thickness.get("method") != (
        "sampled_inward_normal_ray_uniform_grid_exact_triangle_intersection"
    ):
        raise ValueError("méthode de mesure d'épaisseur F37 inattendue")
    requested = int(thickness["requested_sample_count"])
    resolved = int(thickness["sample_count"])
    unresolved = int(thickness["unresolved_sample_count"])
    minimum_fraction = float(thickness["minimum_resolved_fraction"])
    references = int(thickness["spatial_index_triangle_references"])
    reference_limit = int(thickness["spatial_index_reference_limit"])
    if (
        requested <= 0
        or resolved + unresolved != requested
        or resolved < math.ceil(minimum_fraction * requested)
        or not 0.95 <= minimum_fraction <= 1.0
        or references < 0
        or references > reference_limit
    ):
        raise ValueError("couverture ou borne mémoire du contrôle d'épaisseur incohérente")
    thickness_p01 = float(thickness["p01_mm_if_scale_is_mm"])
    if not math.isfinite(thickness_p01) or thickness_p01 <= 0.0:
        raise ValueError("épaisseur p01 F37 non positive")
    expected_gates = {
        "watertight_single_body": bool(
            head_mesh["result"]["watertight"] and head_mesh["result"]["body_count"] == 1
        ),
        "fits_build_envelope": bool(selected["fits_250x250x325_mm"]),
        "sampled_p01_thickness_at_least_1_5_mm": thickness_p01 >= 1.5,
        "coarse_trapped_void_volume_zero": trapped_count == 0,
        "coarse_layer_support_fraction_below_0_5_percent": unsupported_fraction <= 0.005,
    }
    for name, expected in expected_gates.items():
        if print_gates.get(name) is not expected:
            raise ValueError(f"porte LPBF dérivée incohérente: {name}")


def build_payload(
    printability: dict,
    head_mesh: dict,
    locked: dict,
    contract: dict,
    cad: dict,
    inputs: dict,
) -> dict:
    selected = printability["selected"]
    voxel = printability["voxel_audit"]
    thickness = printability["thickness_audit"]
    stress = locked["results"]
    orientations = sorted(printability["orientations"], key=lambda item: item["score"])
    top = [compact_orientation(item) for item in orientations[:8]]
    allowances = contract["machining_allowances_mm_if_scale_is_mm"]

    assumed_density = float(printability["assumed_density_kg_m3"])
    build_volume_cm3 = printability["head_mass_kg"] * 1.0e6 / assumed_density
    support_proxy_ratio = selected["column_support_volume_proxy_mm3"] / (build_volume_cm3 * 1000.0)
    hydraulic_passages = {
        "feed_mm": contract["oil_system"]["head_feed_lateral"]["diameter_mm"],
        "header_mm": contract["oil_system"]["head_header"]["diameter_mm"],
        "metering_branches_mm": contract["oil_system"]["four_metering_branches_diameter_mm"],
        "carrier_gallery_mm": contract["oil_system"]["carrier_gallery_diameter_mm"],
        "returns_mm": contract["oil_system"]["return_drains"]["diameter_mm"],
    }

    gates = {
        "conditional_build_envelope_fit": bool(selected["fits_250x250x325_mm"]),
        "candidate_bare_head_mass_below_f36_2_83_kg_target": bool(
            printability["head_mass_kg"] <= 2.83
        ),
        "f37_mesh_watertight_single_body": bool(printability["gates"]["watertight_single_body"]),
        "coarse_trapped_void_screen_zero": bool(
            printability["gates"]["coarse_trapped_void_volume_zero"]
        ),
        "absolute_scale_confirmed": bool(contract["release_gates"]["absolute_scale_confirmed"]),
        "whole_head_single_valid_brep": bool(contract["release_gates"]["whole_head_single_valid_brep"]),
        "sampled_p01_thickness_at_least_1_5_mm": bool(
            printability["gates"]["sampled_p01_thickness_at_least_1_5_mm"]
        ),
        "coarse_layer_support_fraction_below_0_5_percent": bool(
            printability["gates"]["coarse_layer_support_fraction_below_0_5_percent"]
        ),
        "support_topology_sliced_and_reviewed": False,
        "powder_removal_physically_demonstrated": False,
        "machine_parameter_set_and_powder_lot_qualified": False,
        "printed_coupon_material_card_at_temperature": False,
        "calibrated_layer_activation_distortion_model": False,
        "machining_datums_and_tolerance_stack_validated": False,
        "ct_fpi_dimensional_and_pressure_acceptance_complete": False,
        "metal_print_authorized": False,
    }

    return {
        "schema_version": "1.0.0",
        "phase": "F37",
        "status": "lpbf_route_defined_virtual_screen_complete_release_blocked",
        "classification": "manufacturing_route_and_virtual_screen_not_build_release",
        "inputs": inputs,
        "validated_linkage": {
            "printability_head_sha256": printability["inputs"]["head_sha256"],
            "f37_head_artifact_sha256": head_mesh["local_only_artifacts"][
                "917-head-f37-printable-proof.local.stl"
            ]["sha256"],
            "head_sha256_equal": True,
            "printability_geometry_report_sha256": printability["inputs"][
                "geometry_report_sha256"
            ],
            "f37_head_geometry_report_sha256": head_mesh["inputs"][
                "geometry_report_sha256"
            ],
            "geometry_report_sha256_equal": True,
        },
        "candidate_build": {
            "process": "LPBF_aluminium_candidate",
            "material_candidate": contract["component_material_and_load_screen"]["head"]["candidate"],
            "orientation": selected["id"],
            "orientation_meaning": (
                "axe +y du scan vers le haut de la machine; flanc admission du scan vers le plateau"
            ),
            "transform": selected["transform"],
            "envelope_mm_if_scale_is_mm": selected["extents_mm_if_scale_is_mm"],
            "layer_height_um_candidate_only": 50.0,
            "layer_count": selected["layer_count_at_50_um"],
            "estimated_exposure_hours_at_60_cm3_h_excludes_overheads": printability[
                "estimated_build_hours_at_60_cm3_per_hour"
            ],
            "assumed_density_kg_m3": assumed_density,
            "head_volume_cm3_from_mass_and_assumed_density": build_volume_cm3,
            "head_mass_kg_if_scale_and_density_are_correct": printability["head_mass_kg"],
            "f36_comparative_bare_head_mass_target_kg": 2.83,
            "downward_overhang_area_cm2": selected["downward_overhang_area_mm2"] / 100.0,
            "projected_support_area_cm2": selected["projected_support_area_mm2"] / 100.0,
            "column_support_volume_proxy_cm3_not_sliced_support": selected[
                "column_support_volume_proxy_mm3"
            ]
            / 1000.0,
            "column_support_proxy_to_part_volume_ratio": support_proxy_ratio,
            "coarse_unsupported_fraction_percent": voxel["unsupported_fraction"] * 100.0,
            "coarse_trapped_void_volume_cm3": voxel["trapped_void_volume_mm3"] / 1000.0,
            "voxel_pitch_mm": voxel["pitch_mm"],
            "voxel_method": voxel["method"],
            "winding_chunk_triangles": voxel["winding_chunk_triangles"],
            "sampled_p01_thickness_mm": thickness["p01_mm_if_scale_is_mm"],
            "sampled_p05_thickness_mm": thickness["p05_mm_if_scale_is_mm"],
            "thickness_method": thickness["method"],
            "thickness_resolved_samples": thickness["sample_count"],
            "thickness_requested_samples": thickness["requested_sample_count"],
            "thickness_spatial_index_triangle_references": thickness[
                "spatial_index_triangle_references"
            ],
            "thickness_spatial_index_reference_limit": thickness[
                "spatial_index_reference_limit"
            ],
            "free_contraction_mm_for_uniform_280k_screen": printability["free_contraction_mm_280k"],
            "top_orientation_candidates": top,
        },
        "support_strategy": {
            "status": "to_be_sliced_on_final_single_brep",
            "intent": [
                "ajouter des plots sacrificiels usinables sur le flanc admission non fonctionnel",
                "ancrer les masses principales par supports massifs segmentes et les ailettes par supports legers",
                "interdire les supports sur sieges, guides, deck final et surfaces de joint",
                "eviter les volumes de support aveugles dans les ports et toutes les galeries d'huile",
                "prevoir acces outil et trajectoire de retrait pour chaque support",
            ],
            "acceptance": [
                "unsupported_fraction_after_final_slicing_below_0_5_percent",
                "every_support_has_documented_removal_access",
                "thermal_islands_reviewed_layer_by_layer",
                "no_support_contacts_a_final_functional_surface",
            ],
            "current_limit": (
                "le proxy de colonnes F37 ne contient ni geometrie de support, ni interface plateau, ni scan-path"
            ),
        },
        "powder_and_oil_gallery_strategy": {
            "nominal_passage_diameters_mm_if_scale_is_mm": hydraulic_passages,
            "route": [
                "conserver chaque galerie droite et ouverte a une extremite de nettoyage",
                "ne pas accepter les branches de dosage de 3 mm en cote finale as-built",
                "imprimer des pilotes puis percer/aleser les branches a 3.00 +/- 0.05 mm",
                "depoudrer par retournements indexes, vibration et gaz sec filtre jusqu'a masse stable",
                "inspecter les galeries par CT puis endoscope quand la ligne de vue le permet",
                "rincer en circuit ferme, filtrer les effluents et verifier la proprete particulaire",
                "poser les bouchons seulement apres epreuve de debit, pression et proprete",
            ],
            "current_limit": (
                "le noyau OCCT est connecte et ouvert par definition mais n'est pas soustrait d'un B-Rep complet de culasse"
            ),
            "physical_demo_required": True,
        },
        "machining_stock_mm_if_scale_is_mm": allowances,
        "manufacturing_route": [
            {
                "op": 10,
                "name": "gel_conception",
                "acceptance": "un seul B-Rep de culasse, echelle et interfaces 917 confirmees, datums A/B/C liberes",
            },
            {
                "op": 20,
                "name": "qualification_matiere_procede",
                "acceptance": (
                    "lot poudre, machine, orientation, parametres, traitement HT1/HT2 et eprouvettes temoins qualifies"
                ),
            },
            {
                "op": 30,
                "name": "slicing_et_revues",
                "acceptance": (
                    "supports reels, recoater clearance, dose thermique, trajectoires laser et evacuation poudre signes"
                ),
            },
            {
                "op": 40,
                "name": "construction_lpbf",
                "acceptance": "journaux machine, atmosphere, O2, poudre, images couche et coupons lies au numero de serie",
            },
            {
                "op": 50,
                "name": "traitement_sur_plaque",
                "acceptance": (
                    "cycle fournisseur qualifie applique avant separation; aucune recette temperature/temps inventee"
                ),
            },
            {
                "op": 60,
                "name": "depoudrage_controle",
                "acceptance": "masse stable, CT galeries, endoscopie accessible et proprete particulaire acceptees",
            },
            {
                "op": 70,
                "name": "separation_supports",
                "acceptance": "decoupe fil/usinage sans entaille des ailettes ni des futures surfaces fonctionnelles",
            },
            {
                "op": 80,
                "name": "traitement_final",
                "acceptance": "HT2 et eventuel HIP seulement suivant une gamme qualifiee par coupons et CT",
            },
            {
                "op": 90,
                "name": "ct_fpi_dimensionnel_intermediaire",
                "acceptance": "porosite, fissures, inclusions et deformation compares a des criteres signes",
            },
            {
                "op": 100,
                "name": "usinage_fonctionnel",
                "acceptance": (
                    "deck, registre, logements sieges/guides, porte-culbuteurs, goujons et filetages depuis A/B/C"
                ),
            },
            {
                "op": 110,
                "name": "finition_galeries",
                "acceptance": "perçage/alesage calibre, ebavurage, lavage, mesure debit et epreuve pression",
            },
            {
                "op": 120,
                "name": "inspection_finale",
                "acceptance": "CMM, rugosite, planitude, CT ciblee, FPI, etancheite, debit et dossier de tracabilite",
            },
            {
                "op": 130,
                "name": "essais_composant",
                "acceptance": "banc flux, cyclage thermique instrumente, puis banc moteur progressif apres revue professionnelle",
            },
        ],
        "locked_plate_screen": {
            "geometry_classification": "F36_parent_locked_plate_proxy_not_F37_final_mesh",
            "f37_final_mesh_thermomechanical_build_simulated": False,
            "solver": locked["solver"],
            "mesh_pitch_mm_if_scale_is_mm": locked["mesh"]["pitch_mm_if_scale_is_mm"],
            "hexahedra": locked["mesh"]["hexahedra"],
            "nodes": locked["mesh"]["nodes"],
            "uniform_temperature_delta_k": locked["thermal_load"]["delta_temperature_k"],
            "von_mises_p95_mpa": stress["von_mises_p95_mpa"],
            "von_mises_p99_mpa": stress["von_mises_p99_mpa"],
            "von_mises_max_mpa": stress["von_mises_max_mpa"],
            "maximum_displacement_mm": stress["maximum_displacement_mm"],
            "interpretation": (
                "majorant lineaire qualitatif de bridage; les valeurs au-dela de la limite elastique ne sont pas physiques"
            ),
            "missing_physics": [
                "activation couche par couche",
                "historique thermique laser/recoat",
                "plasticite et relaxation de contrainte",
                "fluage a chaud",
                "supports et contact plateau calibres",
                "anisotropie et retrait issus de coupons",
                "separation du plateau et sequence d'usinage",
            ],
        },
        "equations": {
            "free_thermal_contraction": "abs(delta_L_i) = alpha * abs(delta_T) * L_i",
            "build_time_exposure_only": "t_h = V_part_cm3 / 60_cm3_per_h",
            "support_proxy_ratio": "R_proxy = V_column_proxy / V_part",
            "note": "ces equations sont des controles d'ordre de grandeur, pas une simulation procede calibree",
        },
        "inspection_and_test_plan": {
            "witnesses_per_build": [
                "densite et metallographie",
                "traction ambiante et a chaud dans les orientations critiques",
                "conductivite thermique a chaud",
                "fatigue thermique/mecanique representant le deck",
            ],
            "part_inspection": [
                "CT volumique avant et apres usinage critique",
                "ressuage fluorescent apres supports et apres usinage",
                "CMM des datums, deck, registre, sieges, guides et axes culbuteurs",
                "mesure rugosite et planitude",
                "epreuve pneumatique/hydraulique des conduits selon plan signe",
                "debit individuel des quatre branches d'huile",
            ],
        },
        "gates": gates,
        "decision": {
            "metal_print_authorized": False,
            "reason": (
                "echelle et B-Rep complet non confirmes; volume ferme, epaisseur et supports echouent; "
                "procede, coupons et inspection non qualifies"
            ),
        },
    }


def render_board(payload: dict, path: Path) -> None:
    # La validation du plan ne doit pas dépendre de la pile de rendu.
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig = plt.figure(figsize=(20, 11.25), facecolor="#071018")
    grid = fig.add_gridspec(2, 2, left=0.095, right=0.97, top=0.78, bottom=0.07, wspace=0.18, hspace=0.30)
    gold = "#f6b73c"
    cyan = "#42cbe8"
    red = "#ff5d62"
    green = "#55d187"
    text = "#eef5f8"
    muted = "#9fb1bd"
    panel = "#101e28"

    fig.suptitle("F37 — dossier LPBF / fabrication virtuelle", color=text, fontsize=27, fontweight="bold", y=0.965)
    fig.text(
        0.5,
        0.905,
        "Orientation • supports • retrait • usinage • CT/CND",
        color=gold,
        fontsize=15,
        ha="center",
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.855,
        "NON LIBÉRÉ POUR FABRICATION",
        color=red,
        fontsize=14,
        ha="center",
        fontweight="bold",
    )

    ax = fig.add_subplot(grid[0, 0], facecolor=panel)
    top = payload["candidate_build"]["top_orientation_candidates"][:6][::-1]
    labels = [item["id"].replace("scan_y_down", "y↓") for item in top]
    scores = [item["score"] / 1.0e6 for item in top]
    colors = [green if item["id"] == payload["candidate_build"]["orientation"] else gold for item in top]
    ax.barh(labels, scores, color=colors, edgecolor="none")
    ax.set_title("Classement orientation — score proxy plus bas = mieux", color=text, fontsize=15, pad=14)
    ax.set_xlabel("score proxy [10⁶ mm³ équivalent]", color=muted)
    ax.tick_params(colors=text, labelsize=10)
    ax.grid(axis="x", color="#34505e", alpha=0.35)
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax = fig.add_subplot(grid[0, 1], facecolor=panel)
    stress = payload["locked_plate_screen"]
    names = ["p95", "p99", "maximum"]
    values = [stress["von_mises_p95_mpa"], stress["von_mises_p99_mpa"], stress["von_mises_max_mpa"]]
    ax.bar(names, values, color=[green, gold, red], width=0.55)
    ax.set_title("Proxy F36 plaque bloquée — non calibré", color=text, fontsize=15, pad=14)
    ax.set_ylabel("von Mises [MPa]", color=muted)
    ax.tick_params(colors=text)
    ax.grid(axis="y", color="#34505e", alpha=0.35)
    for index, value in enumerate(values):
        ax.text(index, value + 35, f"{value:.0f}", ha="center", color=text, fontsize=12, fontweight="bold")
    ax.text(
        0.02,
        0.96,
        f"Déplacement max: {stress['maximum_displacement_mm']:.3f} mm\n"
        "Sans plasticité / couches / supports réels",
        transform=ax.transAxes,
        color=muted,
        fontsize=11,
        va="top",
    )
    for spine in ax.spines.values():
        spine.set_visible(False)

    ax = fig.add_subplot(grid[1, 0], facecolor=panel)
    ax.axis("off")
    build = payload["candidate_build"]
    facts = [
        ("Orientation candidate", build["orientation"], True),
        ("Enveloppe conditionnelle", " × ".join(f"{x:.1f}" for x in build["envelope_mm_if_scale_is_mm"]) + " mm", payload["gates"]["conditional_build_envelope_fit"]),
        ("Couches candidates", f"{build['layer_count']:,}".replace(",", " ") + " @ 50 µm", True),
        ("Surplomb descendant", f"{build['downward_overhang_area_cm2']:.1f} cm²", True),
        ("Voxels sans appui", f"{build['coarse_unsupported_fraction_percent']:.3f} % (cible ≤ 0,5 %)", payload["gates"]["coarse_layer_support_fraction_below_0_5_percent"]),
        ("Volume fermé", f"{build['coarse_trapped_void_volume_cm3']:.3f} cm³ (cible 0)", payload["gates"]["coarse_trapped_void_screen_zero"]),
        ("Épaisseur p01", f"{build['sampled_p01_thickness_mm']:.2f} mm (cible ≥ 1,5 mm)", payload["gates"]["sampled_p01_thickness_at_least_1_5_mm"]),
        ("Retrait libre", " / ".join(f"{x:.2f}" for x in build["free_contraction_mm_for_uniform_280k_screen"]) + " mm", True),
        ("Temps laser seul", f"{build['estimated_exposure_hours_at_60_cm3_h_excludes_overheads']:.1f} h", True),
    ]
    ax.set_title("Fiche construction candidate", color=text, fontsize=15, pad=14)
    y = 0.88
    for label, value, passed in facts:
        ax.text(0.05, y, label, color=muted, fontsize=12, va="center")
        ax.text(0.96, y, value, color=text if passed else red, fontsize=12, va="center", ha="right", fontweight="bold")
        y -= 0.105

    ax = fig.add_subplot(grid[1, 1], facecolor=panel)
    ax.axis("off")
    ax.set_title("Gamme et portes de libération", color=text, fontsize=15, pad=14)
    route = ["CAO / datums", "Coupons + lot poudre", "Slicing + supports", "LPBF + logs", "HT + dépoudrage", "CT/FPI + usinage", "Bancs physiques"]
    y0 = 0.86
    for index, label in enumerate(route):
        x = 0.08 + (index % 2) * 0.48
        y = y0 - (index // 2) * 0.16
        color = cyan if index < 5 else gold
        ax.text(x, y, f"{index + 1}. {label}", color=color, fontsize=12, fontweight="bold", va="center")
    gate_items = list(payload["gates"].items())
    passed = sum(bool(value) for _, value in gate_items)
    ax.text(0.08, 0.17, f"Portes documentaires franchies: {passed}/{len(gate_items)}", color=text, fontsize=14, fontweight="bold")
    ax.text(
        0.08,
        0.08,
        "Bloquants: échelle • B-Rep complet • épaisseur • supports • paramètres machine • coupons • CT/CND",
        color=red,
        fontsize=10.5,
    )

    fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    printability = load_json(args.printability)
    head_mesh = load_json(args.f37_head_mesh_report)
    locked = load_json(args.locked_plate)
    contract = load_json(args.f37_contract)
    cad = load_json(args.f37_cad_report)

    validate_inputs(printability, head_mesh, locked, contract, cad, args)

    inputs = {
        "f37_printability_report": {"path": str(args.printability), "sha256": sha256(args.printability)},
        "f37_head_mesh_report": {"path": str(args.f37_head_mesh_report), "sha256": sha256(args.f37_head_mesh_report)},
        "f36_locked_plate_report": {"path": str(args.locked_plate), "sha256": sha256(args.locked_plate)},
        "f37_contract": {"path": str(args.f37_contract), "sha256": sha256(args.f37_contract)},
        "f37_cad_report": {"path": str(args.f37_cad_report), "sha256": sha256(args.f37_cad_report)},
    }
    payload = build_payload(printability, head_mesh, locked, contract, cad, inputs)
    report_path = args.output / "f37-lpbf-manufacturing-report.json"
    board_path = args.output / "917-head-f37-lpbf-manufacturing.png"
    write_json(report_path, payload)
    render_board(payload, board_path)

    payload["artifacts"] = {
        report_path.name: {"bytes": report_path.stat().st_size, "sha256_before_artifact_field": sha256(report_path)},
        board_path.name: {"bytes": board_path.stat().st_size, "sha256": sha256(board_path)},
    }
    write_json(report_path, payload)
    print(report_path)
    print(board_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
