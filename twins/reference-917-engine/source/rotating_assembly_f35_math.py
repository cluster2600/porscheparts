#!/usr/bin/env python3
"""Cinématique analytique F35 d'un V12 à 180° à six manetons partagés.

Le module utilise uniquement la bibliothèque standard. Il décrit six stations
géométriques le long de l'axe X du vilebrequin. Chaque maneton est partagé
par un piston du banc A (+Y) et un piston du banc B (-Y). Les axes de piston
restent dans le plan Z=0 et chaque bielle ferme exactement le segment entre le
centre du maneton et le centre de l'axe de piston.

Les identifiants sont volontairement géométriques. Le module ne consomme ni
ordre d'allumage, ni numérotation historique de cylindres : ces deux mappings
restent des données de provenance à résoudre ailleurs. Les longueurs et phases
passées au module restent donc des entrées de modèle, pas des cotes de
fabrication ou une preuve de performance.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


Vector3 = tuple[float, float, float]

CRANK_AXIS: Vector3 = (1.0, 0.0, 0.0)
BANK_AXES: dict[str, Vector3] = {
    "bank_A": (0.0, 1.0, 0.0),
    "bank_B": (0.0, -1.0, 0.0),
}
BANK_SIGNS: dict[str, int] = {"bank_A": 1, "bank_B": -1}
EXPECTED_STATION_COUNT = 6
EXPECTED_PISTON_COUNT = 12
EXPECTED_CONNECTING_ROD_COUNT = 12
FULL_ENGINE_CYCLE_DEG = 720.0

# Autorité de placement axial commune aux exports STEP et USD. Deux bielles
# identiques sont présentées côte à côte sur chaque maneton avec un jeu visuel
# positif de 6 % de leur largeur. Cette topologie reste une hypothèse F35 : elle
# ne dimensionne pas la largeur réelle du maneton et n'autorise aucun contact.
PAIRED_ROD_AXIAL_CLEARANCE_FACTOR = 0.06

# Hypothèse géométrique symétrique de type inline-six pour les six stations.
# Elle ne constitue ni un calage Porsche historique, ni un mapping d'ordre
# d'allumage, ni une cote libérée. Les consommateurs doivent conserver ce statut
# de design study lorsqu'ils l'emploient dans une CAO ou un stage USD.
DESIGN_CRANKPIN_PHASES_DEG: tuple[float, ...] = (
    0.0,
    120.0,
    240.0,
    240.0,
    120.0,
    0.0,
)


def _is_finite_number(value: object) -> bool:
    """Retourne vrai uniquement pour un nombre réel fini, hors booléen."""

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _finite_float(value: object, label: str) -> float:
    """Convertit une entrée numérique finie ou lève une erreur explicite."""

    if not _is_finite_number(value):
        raise ValueError(f"{label} must be a finite real number")
    return float(value)


def _positive_float(value: object, label: str) -> float:
    """Valide une longueur strictement positive et finie."""

    result = _finite_float(value, label)
    if result <= 0.0:
        raise ValueError(f"{label} must be greater than zero")
    return result


def _vector_subtract(first: Vector3, second: Vector3) -> Vector3:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def _vector_midpoint(first: Vector3, second: Vector3) -> Vector3:
    return (
        (first[0] + second[0]) * 0.5,
        (first[1] + second[1]) * 0.5,
        (first[2] + second[2]) * 0.5,
    )


def _vector_norm(vector: Vector3) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _normalise_phase_deg(value: float) -> float:
    """Normalise une phase géométrique dans l'intervalle [0, 360[."""

    phase = value % 360.0
    return 0.0 if math.isclose(phase, 360.0, abs_tol=1e-12) else phase


def paired_rod_axial_layout_mm(connecting_rod_width_mm: float) -> dict[str, Any]:
    """Définit le décalage axial non recouvrant de la paire de bielles.

    Le profil CAO de bielle est centré sur X et sa largeur vaut
    ``connecting_rod_width_mm``. Les centres sont donc séparés de la largeur
    plus un jeu strictement positif. Cette fonction est l'unique autorité de
    transform consommée par les assemblages STEP et USD.
    """

    width = _positive_float(connecting_rod_width_mm, "connecting_rod_width_mm")
    clearance = width * PAIRED_ROD_AXIAL_CLEARANCE_FACTOR
    center_separation = width + clearance
    half_separation = center_separation * 0.5
    return {
        "topology": "side_by_side_visual_design_hypothesis",
        "rod_width_mm": width,
        "clearance_mm": clearance,
        "center_separation_mm": center_separation,
        "bank_offsets_mm": {
            "bank_A": half_separation,
            "bank_B": -half_separation,
        },
        "shared_crankpin_width_validated": False,
        "physical_contact_validated": False,
    }


def paired_rod_axial_offset_mm(bank: str, connecting_rod_width_mm: float) -> float:
    """Retourne le décalage X d'une bielle depuis la station de maneton."""

    if bank not in BANK_SIGNS:
        raise ValueError(f"unknown bank {bank!r}; expected one of {sorted(BANK_SIGNS)}")
    return float(paired_rod_axial_layout_mm(connecting_rod_width_mm)["bank_offsets_mm"][bank])


def validate_model_inputs(
    station_x_mm: Sequence[float],
    crankpin_phases_deg: Sequence[float],
    crank_radius_mm: float,
    connecting_rod_length_mm: float,
) -> dict[str, Any]:
    """Valide les six stations et les dimensions minimales du modèle.

    Les phases sont géométriques et peuvent se répéter : un vilebrequin à six
    manetons peut posséder plusieurs stations à la même orientation. La fonction
    ne leur associe jamais un numéro de cylindre ou une position dans l'ordre
    d'allumage.
    """

    errors: list[str] = []
    try:
        radius = _positive_float(crank_radius_mm, "crank_radius_mm")
    except ValueError as exc:
        errors.append(str(exc))
        radius = math.nan
    try:
        rod_length = _positive_float(connecting_rod_length_mm, "connecting_rod_length_mm")
    except ValueError as exc:
        errors.append(str(exc))
        rod_length = math.nan

    stations = list(station_x_mm)
    phases = list(crankpin_phases_deg)
    if len(stations) != EXPECTED_STATION_COUNT:
        errors.append(
            f"station_x_mm must contain exactly {EXPECTED_STATION_COUNT} axial stations"
        )
    if len(phases) != EXPECTED_STATION_COUNT:
        errors.append(
            f"crankpin_phases_deg must contain exactly {EXPECTED_STATION_COUNT} phases"
        )

    finite_stations = [_is_finite_number(value) for value in stations]
    finite_phases = [_is_finite_number(value) for value in phases]
    if not all(finite_stations):
        errors.append("every station_x_mm value must be finite")
    if not all(finite_phases):
        errors.append("every crankpin phase must be finite")

    if all(finite_stations) and len({float(value) for value in stations}) != len(stations):
        errors.append("station_x_mm values must be unique")
    normalised_phases = (
        [_normalise_phase_deg(float(value)) for value in phases] if all(finite_phases) else []
    )
    unique_phase_count = len({round(value, 12) for value in normalised_phases})

    if math.isfinite(radius) and math.isfinite(rod_length) and rod_length <= radius:
        errors.append("connecting_rod_length_mm must be greater than crank_radius_mm")

    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "station_count": len(stations),
        "normalised_geometric_phases_deg": normalised_phases,
        "unique_geometric_phase_count": unique_phase_count,
        "historical_cylinder_mapping_used": False,
        "firing_order_used": False,
    }


def geometric_phase_table(crankpin_phases_deg: Sequence[float]) -> list[dict[str, Any]]:
    """Construit la table des six manetons sans injecter d'identité historique."""

    phases = list(crankpin_phases_deg)
    if len(phases) != EXPECTED_STATION_COUNT or not all(
        _is_finite_number(value) for value in phases
    ):
        raise ValueError("six finite geometric crankpin phases are required")
    normalised = [_normalise_phase_deg(float(value)) for value in phases]
    table = []
    for index, phase in enumerate(normalised, start=1):
        station_id = f"station_{index:02d}"
        table.append(
            {
                "station_id": station_id,
                "geometric_phase_deg": phase,
                "shared_crankpin": True,
                "members": [
                    {
                        "geometric_id": f"bank_A_{station_id}",
                        "bank": "bank_A",
                        "historical_cylinder_id": None,
                        "firing_order_position": None,
                    },
                    {
                        "geometric_id": f"bank_B_{station_id}",
                        "bank": "bank_B",
                        "historical_cylinder_id": None,
                        "firing_order_position": None,
                    },
                ],
            }
        )
    return table


def crankpin_position_mm(
    station_x_mm: float,
    crank_radius_mm: float,
    crank_angle_deg: float,
    geometric_phase_deg: float,
) -> Vector3:
    """Retourne le centre d'un maneton autour de l'axe X du vilebrequin."""

    station_x = _finite_float(station_x_mm, "station_x_mm")
    radius = _positive_float(crank_radius_mm, "crank_radius_mm")
    angle = math.radians(
        _finite_float(crank_angle_deg, "crank_angle_deg")
        + _finite_float(geometric_phase_deg, "geometric_phase_deg")
    )
    return (station_x, radius * math.cos(angle), radius * math.sin(angle))


def piston_pin_position_mm(
    bank: str,
    crankpin_mm: Vector3,
    connecting_rod_length_mm: float,
) -> tuple[Vector3, float]:
    """Ferme la bielle sur l'axe de piston d'un des deux bancs.

    Le maneton est commun aux deux bancs. L'axe de piston est contraint à
    `Z=0` et à la même station X. La racine positive sélectionne toujours la
    solution extérieure au carter. Le second élément retourné est la coordonnée
    radiale positive mesurée depuis l'axe du vilebrequin.
    """

    if bank not in BANK_SIGNS:
        raise ValueError(f"unknown bank {bank!r}; expected one of {sorted(BANK_SIGNS)}")
    if len(crankpin_mm) != 3 or not all(_is_finite_number(value) for value in crankpin_mm):
        raise ValueError("crankpin_mm must contain three finite coordinates")
    rod_length = _positive_float(connecting_rod_length_mm, "connecting_rod_length_mm")
    x, crankpin_y, crankpin_z = (float(value) for value in crankpin_mm)
    radicand = rod_length * rod_length - crankpin_z * crankpin_z
    tolerance = max(1.0, rod_length * rod_length) * 1e-14
    if radicand < -tolerance:
        raise ValueError("connecting rod cannot reach the bank axis for this crank position")
    radial_projection = math.sqrt(max(0.0, radicand))
    bank_sign = BANK_SIGNS[bank]
    piston_y = crankpin_y + bank_sign * radial_projection
    outward_coordinate = bank_sign * piston_y
    return (x, piston_y, 0.0), outward_coordinate


def connecting_rod_state(
    geometric_id: str,
    bank: str,
    crankpin_mm: Vector3,
    piston_pin_mm: Vector3,
    nominal_length_mm: float,
) -> dict[str, Any]:
    """Décrit une bielle par ses deux centres et son erreur de fermeture."""

    if not isinstance(geometric_id, str) or not geometric_id:
        raise ValueError("geometric_id must be a non-empty string")
    if bank not in BANK_SIGNS:
        raise ValueError(f"unknown bank {bank!r}")
    nominal_length = _positive_float(nominal_length_mm, "nominal_length_mm")
    vector = _vector_subtract(piston_pin_mm, crankpin_mm)
    actual_length = _vector_norm(vector)
    outward_component = sum(
        vector[index] * BANK_AXES[bank][index] for index in range(3)
    )
    signed_tilt_deg = math.degrees(
        math.atan2(BANK_SIGNS[bank] * vector[2], outward_component)
    )
    return {
        "geometric_id": geometric_id,
        "bank": bank,
        "big_end_center_mm": crankpin_mm,
        "small_end_center_mm": piston_pin_mm,
        "center_mm": _vector_midpoint(crankpin_mm, piston_pin_mm),
        "vector_big_to_small_mm": vector,
        "nominal_length_mm": nominal_length,
        "actual_length_mm": actual_length,
        "closure_error_mm": actual_length - nominal_length,
        "signed_tilt_about_x_deg": signed_tilt_deg,
    }


def assembly_sample(
    *,
    crank_angle_deg: float,
    station_x_mm: Sequence[float],
    crankpin_phases_deg: Sequence[float],
    crank_radius_mm: float,
    connecting_rod_length_mm: float,
) -> dict[str, Any]:
    """Génère un état complet : 6 manetons, 12 pistons et 12 bielles."""

    inputs = validate_model_inputs(
        station_x_mm,
        crankpin_phases_deg,
        crank_radius_mm,
        connecting_rod_length_mm,
    )
    if inputs["status"] != "passed":
        raise ValueError("; ".join(inputs["errors"]))
    angle = _finite_float(crank_angle_deg, "crank_angle_deg")
    station_values = [float(value) for value in station_x_mm]
    phase_table = geometric_phase_table(crankpin_phases_deg)
    crankpins = []
    piston_count = 0
    rod_count = 0
    for station_x, phase in zip(station_values, phase_table):
        crankpin = crankpin_position_mm(
            station_x,
            crank_radius_mm,
            angle,
            phase["geometric_phase_deg"],
        )
        pistons = []
        for member in phase["members"]:
            bank = member["bank"]
            geometric_id = member["geometric_id"]
            pin, outward = piston_pin_position_mm(
                bank,
                crankpin,
                connecting_rod_length_mm,
            )
            rod = connecting_rod_state(
                f"connecting_rod_{geometric_id}",
                bank,
                crankpin,
                pin,
                connecting_rod_length_mm,
            )
            pistons.append(
                {
                    "geometric_id": geometric_id,
                    "bank": bank,
                    "bank_axis": BANK_AXES[bank],
                    "historical_cylinder_id": None,
                    "firing_order_position": None,
                    "piston_pin_center_mm": pin,
                    "outward_coordinate_mm": outward,
                    "connecting_rod": rod,
                }
            )
            piston_count += 1
            rod_count += 1
        crankpins.append(
            {
                "station_id": phase["station_id"],
                "station_x_mm": station_x,
                "geometric_phase_deg": phase["geometric_phase_deg"],
                "shared_by_two_rods": True,
                "center_mm": crankpin,
                "pistons": pistons,
            }
        )
    return {
        "crank_angle_deg": angle,
        "crank_axis": CRANK_AXIS,
        "crankpin_count": len(crankpins),
        "piston_count": piston_count,
        "connecting_rod_count": rod_count,
        "historical_cylinder_mapping_used": False,
        "firing_order_used": False,
        "crankpins": crankpins,
    }


def cycle_angles_deg(step_deg: float = 1.0) -> list[float]:
    """Retourne les angles 0..720 inclus sans accumulation flottante."""

    step = _positive_float(step_deg, "step_deg")
    interval_count_float = FULL_ENGINE_CYCLE_DEG / step
    interval_count = round(interval_count_float)
    if interval_count < 1 or not math.isclose(
        interval_count_float, interval_count, rel_tol=0.0, abs_tol=1e-10
    ):
        raise ValueError("step_deg must divide the 720 degree engine cycle exactly")
    angles = [index * step for index in range(interval_count + 1)]
    angles[-1] = FULL_ENGINE_CYCLE_DEG
    return angles


def generate_cycle_samples(
    *,
    station_x_mm: Sequence[float],
    crankpin_phases_deg: Sequence[float],
    crank_radius_mm: float,
    connecting_rod_length_mm: float,
    step_deg: float = 1.0,
) -> list[dict[str, Any]]:
    """Génère le cycle analytique complet entre 0 et 720° inclus."""

    inputs = validate_model_inputs(
        station_x_mm,
        crankpin_phases_deg,
        crank_radius_mm,
        connecting_rod_length_mm,
    )
    if inputs["status"] != "passed":
        raise ValueError("; ".join(inputs["errors"]))
    return [
        assembly_sample(
            crank_angle_deg=angle,
            station_x_mm=station_x_mm,
            crankpin_phases_deg=crankpin_phases_deg,
            crank_radius_mm=crank_radius_mm,
            connecting_rod_length_mm=connecting_rod_length_mm,
        )
        for angle in cycle_angles_deg(step_deg)
    ]


def _all_numeric_values_finite(value: object) -> bool:
    """Vérifie récursivement les nombres d'un artefact d'échantillonnage."""

    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(_all_numeric_values_finite(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_numeric_values_finite(item) for item in value)
    return False


def validate_cycle_samples(
    samples: Sequence[dict[str, Any]],
    *,
    expected_stroke_mm: float,
    connecting_rod_length_mm: float,
    closure_tolerance_mm: float = 1e-9,
    stroke_tolerance_mm: float = 1e-9,
) -> dict[str, Any]:
    """Valide comptes, finitude, course et fermeture des douze bielles.

    Cette validation prouve uniquement les identités cinématiques du modèle
    analytique. Elle ne valide ni jeux, ni contacts, ni masses, ni contraintes.
    """

    stroke = _positive_float(expected_stroke_mm, "expected_stroke_mm")
    rod_length = _positive_float(connecting_rod_length_mm, "connecting_rod_length_mm")
    closure_tolerance = _positive_float(closure_tolerance_mm, "closure_tolerance_mm")
    stroke_tolerance = _positive_float(stroke_tolerance_mm, "stroke_tolerance_mm")
    values = list(samples)
    errors: list[str] = []
    if not values:
        errors.append("at least one cycle sample is required")

    finite = all(_all_numeric_values_finite(sample) for sample in values)
    if not finite:
        errors.append("all numeric sample values must be finite")

    piston_positions: dict[str, list[float]] = {}
    maximum_closure_error = 0.0
    count_failures = []
    for sample_index, sample in enumerate(values):
        crankpins = sample.get("crankpins", [])
        pistons = [
            piston
            for crankpin in crankpins
            for piston in crankpin.get("pistons", [])
        ]
        rods = [piston.get("connecting_rod") for piston in pistons]
        if (
            len(crankpins) != EXPECTED_STATION_COUNT
            or len(pistons) != EXPECTED_PISTON_COUNT
            or len(rods) != EXPECTED_CONNECTING_ROD_COUNT
        ):
            count_failures.append(sample_index)
            continue
        for piston, rod in zip(pistons, rods):
            geometric_id = piston.get("geometric_id")
            outward = piston.get("outward_coordinate_mm")
            if not isinstance(geometric_id, str) or not _is_finite_number(outward):
                errors.append(f"sample {sample_index}: invalid piston identity or coordinate")
                continue
            piston_positions.setdefault(geometric_id, []).append(float(outward))
            if not isinstance(rod, dict):
                errors.append(f"sample {sample_index}: missing connecting rod for {geometric_id}")
                continue
            closure_error = rod.get("closure_error_mm")
            actual_length = rod.get("actual_length_mm")
            if not _is_finite_number(closure_error) or not _is_finite_number(actual_length):
                errors.append(f"sample {sample_index}: non-finite rod closure for {geometric_id}")
                continue
            maximum_closure_error = max(maximum_closure_error, abs(float(closure_error)))
            if not math.isclose(
                float(actual_length), rod_length, rel_tol=0.0, abs_tol=closure_tolerance
            ):
                errors.append(f"sample {sample_index}: rod length does not close for {geometric_id}")

    if count_failures:
        errors.append(f"invalid component counts in samples {count_failures}")
    if len(piston_positions) != EXPECTED_PISTON_COUNT:
        errors.append(
            f"expected {EXPECTED_PISTON_COUNT} unique geometric pistons, got {len(piston_positions)}"
        )

    measured_strokes = {
        geometric_id: max(positions) - min(positions)
        for geometric_id, positions in sorted(piston_positions.items())
        if positions
    }
    stroke_failures = {
        geometric_id: measured
        for geometric_id, measured in measured_strokes.items()
        if not math.isclose(measured, stroke, rel_tol=0.0, abs_tol=stroke_tolerance)
    }
    if stroke_failures:
        errors.append(f"piston stroke mismatch: {stroke_failures}")
    if maximum_closure_error > closure_tolerance:
        errors.append(
            f"maximum rod closure error {maximum_closure_error} exceeds {closure_tolerance}"
        )

    sample_angles = [sample.get("crank_angle_deg") for sample in values]
    covers_full_cycle = bool(values) and sample_angles[0] == 0.0 and sample_angles[-1] == 720.0
    if not covers_full_cycle:
        errors.append("samples must cover the inclusive 0..720 degree cycle")

    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "sample_count": len(values),
        "inclusive_cycle_0_720": covers_full_cycle,
        "finite_numeric_values": finite,
        "crankpin_count_per_sample": EXPECTED_STATION_COUNT,
        "piston_count_per_sample": EXPECTED_PISTON_COUNT,
        "connecting_rod_count_per_sample": EXPECTED_CONNECTING_ROD_COUNT,
        "stroke_mm_by_geometric_piston": measured_strokes,
        "expected_stroke_mm": stroke,
        "maximum_connecting_rod_closure_error_mm": maximum_closure_error,
        "historical_cylinder_mapping_used": False,
        "firing_order_used": False,
        "physical_load_validation_authorized": False,
        "manufacturing_release_authorized": False,
    }


def build_and_validate_cycle(
    *,
    station_x_mm: Sequence[float],
    crankpin_phases_deg: Sequence[float],
    stroke_mm: float,
    connecting_rod_length_mm: float,
    step_deg: float = 1.0,
    closure_tolerance_mm: float = 1e-9,
    stroke_tolerance_mm: float = 1e-9,
) -> dict[str, Any]:
    """Construit puis audite un cycle F35 en une seule opération déterministe."""

    stroke = _positive_float(stroke_mm, "stroke_mm")
    samples = generate_cycle_samples(
        station_x_mm=station_x_mm,
        crankpin_phases_deg=crankpin_phases_deg,
        crank_radius_mm=stroke * 0.5,
        connecting_rod_length_mm=connecting_rod_length_mm,
        step_deg=step_deg,
    )
    validation = validate_cycle_samples(
        samples,
        expected_stroke_mm=stroke,
        connecting_rod_length_mm=connecting_rod_length_mm,
        closure_tolerance_mm=closure_tolerance_mm,
        stroke_tolerance_mm=stroke_tolerance_mm,
    )
    return {
        "schema_version": "1.0.0",
        "phase": "F35",
        "model_kind": "analytic_180_degree_v12_six_shared_crankpins",
        "axes": {
            "crankshaft": CRANK_AXIS,
            "bank_A": BANK_AXES["bank_A"],
            "bank_B": BANK_AXES["bank_B"],
        },
        "geometric_phase_table": geometric_phase_table(crankpin_phases_deg),
        "samples": samples,
        "validation": validation,
        "claim_scope": "kinematic_identity_only_not_physical_or_manufacturing_validation",
    }
