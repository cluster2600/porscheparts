#!/usr/bin/env python3
"""Generate one fail-closed reverse-engineering task per Porsche 993 PET part master."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PET_INDEX = ROOT / "twins" / "pet-993" / "index-f0.json"
CONFIGURATION_ROSTER = ROOT / "twins" / "vehicle-993" / "configuration-roster-f0.json"
CONFIGURATION_PART_LINKS = ROOT / "twins" / "vehicle-993" / "configuration-part-links-f0.json"
CONFIGURATION_EXCEPTIONS = ROOT / "twins" / "vehicle-993" / "configuration-exceptions-f0.json"
PROGRAM_DEFINITION = ROOT / "twins" / "vehicle-993" / "program-definition.json"
MANUAL_EVIDENCE_ROUTING = ROOT / "twins" / "vehicle-993" / "manual-evidence-routing-f0.json"
CATALOG_CROSSWALK = ROOT / "twins" / "pet-993" / "catalog-crosswalk-f0.json"
ENGINEERING_EVIDENCE_LINKS = (
    ROOT / "twins" / "pet-993" / "engineering-evidence-links-f0.json"
)
CATALOGUE_TWIN_INDEX = ROOT / "twins" / "catalogue-parts" / "index.json"
OUTPUT = ROOT / "twins" / "pet-993" / "engineering-readiness-f0.json"
DEFAULT_OUTPUT_ROOT = ROOT / "work" / "pet-993" / "engineering-readiness"
SHARD_IDS = tuple("0123456789abcdef")
PLACEHOLDER_MATERIALS = {"", "a_determiner", "unknown", "inconnue", "non determine"}


class ContractError(ValueError):
    """Raised when a PET engineering-readiness contract does not close."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"expected_object:{path}")
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_json(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ContractError(f"expected_jsonl_object:{path}:{line_number}")
                records.append(value)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot_load_jsonl:{path}:{exc}") from exc
    return records


def load_part_masters(index: dict[str, Any]) -> list[dict[str, Any]]:
    shard_records = index.get("output", {}).get("part_master_shards")
    if not isinstance(shard_records, list):
        raise ContractError("part_master_shards")
    masters: list[dict[str, Any]] = []
    for shard in shard_records:
        if not isinstance(shard, dict):
            raise ContractError("part_master_shard_record")
        path_value = shard.get("path")
        expected_sha256 = shard.get("sha256")
        if not isinstance(path_value, str) or not isinstance(expected_sha256, str):
            raise ContractError("part_master_shard_path_digest")
        path = ROOT / path_value
        if sha256_file(path) != expected_sha256:
            raise ContractError(f"part_master_shard_digest:{path_value}")
        records = read_jsonl(path)
        if len(records) != shard.get("record_count"):
            raise ContractError(f"part_master_shard_count:{path_value}")
        masters.extend(records)
    expected_count = index.get("scope", {}).get("part_master_twins")
    if len(masters) != expected_count:
        raise ContractError(f"part_master_total:{len(masters)}:{expected_count}")
    ids = [item.get("twin_id") for item in masters]
    if None in ids or len(ids) != len(set(ids)):
        raise ContractError("part_master_ids")
    return masters


def system_routes(definition: dict[str, Any]) -> dict[str, dict[str, Any]]:
    routes = definition.get("system_routes")
    if not isinstance(routes, list):
        raise ContractError("program_system_routes")
    result = {
        str(route["system_id"]): {
            "criticality": route.get("criticality"),
            "simulation_domain_ids": list(route.get("simulation_domains", [])),
        }
        for route in routes
        if isinstance(route, dict) and route.get("system_id")
    }
    if set(result) != {f"{value}xx" for value in range(10)}:
        raise ContractError("program_system_route_ids")
    return result


def simulation_domain_contracts(definition: dict[str, Any]) -> dict[str, dict[str, Any]]:
    domains = definition.get("simulation_domains")
    policy = definition.get("physicsnemo_policy")
    if not isinstance(domains, dict) or not domains:
        raise ContractError("program_simulation_domains")
    if not isinstance(policy, dict) or policy.get("execution_enabled") is not False:
        raise ContractError("program_physicsnemo_policy")
    verified_models = set(policy.get("verified_model_families", []))
    if not verified_models:
        raise ContractError("program_verified_physicsnemo_models")
    result: dict[str, dict[str, Any]] = {}
    for domain_id, contract in domains.items():
        if not isinstance(contract, dict):
            raise ContractError(f"program_simulation_domain:{domain_id}")
        candidates = contract.get("physicsnemo_candidates", [])
        if not isinstance(candidates, list):
            raise ContractError(f"program_physicsnemo_candidates:{domain_id}")
        unknown = set(candidates) - verified_models
        if unknown:
            raise ContractError(
                f"program_unverified_physicsnemo_candidates:{domain_id}:{sorted(unknown)}"
            )
        result[str(domain_id)] = {
            "reference_method": contract.get("reference_method"),
            "required_geometry": contract.get("required_geometry"),
            "physicsnemo_candidates": [str(value) for value in candidates],
        }
    return result


def criticality_tier(criticalities: set[str]) -> str:
    if any(value.startswith("safety_critical") for value in criticalities):
        return "safety_critical"
    if any(value.startswith("mixed_") for value in criticalities):
        return "mixed_function"
    return "support_and_configuration"


def normalize_description_text(descriptions: list[Any]) -> str:
    text = " ".join(str(value) for value in descriptions if isinstance(value, str))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return f" {' '.join(text.split())} "


def normalize_oem_reference(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


def build_catalogue_proxy_map(index: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    twins = index.get("twins", [])
    if not isinstance(twins, list):
        raise ContractError("catalogue_twin_index_twins")
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for twin in twins:
        if not isinstance(twin, dict):
            raise ContractError("catalogue_twin_record")
        subject = twin.get("subject", {})
        geometry = twin.get("geometry", {})
        validation = twin.get("validation", {})
        reference = subject.get("oem_reference")
        if not isinstance(reference, str) or not reference.strip():
            continue
        normalized_reference = normalize_oem_reference(reference)
        usd_asset = geometry.get("file")
        editable_proxy_asset = geometry.get("editable_proxy_file")
        if not isinstance(usd_asset, str) or not (ROOT / usd_asset).is_file():
            raise ContractError(f"catalogue_proxy_usd:{twin.get('twin_id')}")
        if not isinstance(editable_proxy_asset, str) or not (
            ROOT / editable_proxy_asset
        ).is_file():
            raise ContractError(f"catalogue_proxy_editable:{twin.get('twin_id')}")
        if twin.get("fidelity") != "F1_envelope":
            raise ContractError(f"catalogue_proxy_fidelity:{twin.get('twin_id')}")
        if validation.get("geometry_fit_validated") is not False:
            raise ContractError(f"catalogue_proxy_fit_overclaim:{twin.get('twin_id')}")
        result[normalized_reference].append(
            {
                "proxy_twin_id": twin.get("twin_id"),
                "identity_link_method": "exact_normalized_oem_reference",
                "fidelity": twin.get("fidelity"),
                "representation": twin.get("representation"),
                "usd_asset": usd_asset,
                "editable_proxy_asset": editable_proxy_asset,
                "units": geometry.get("units"),
                "bounding_box_mm": geometry.get("parameters", {}).get(
                    "bounding_box_mm"
                ),
                "accuracy_mm": geometry.get("accuracy_mm"),
                "mass": twin.get("physical", {}).get("mass", {}),
                "material_observation": twin.get("physical", {}).get(
                    "material", {}
                ),
                "material_status": twin.get("physical", {}).get(
                    "material_status"
                ),
                "validation_status": validation.get("status"),
                "geometry_fit_validated": validation.get(
                    "geometry_fit_validated"
                ),
                "simready_status": validation.get("simready_status"),
                "link_status": "F1_envelope_candidate_not_F2_interface_geometry",
            }
        )
    for records in result.values():
        records.sort(key=lambda item: str(item["proxy_twin_id"]))
    return result


def engineering_archetype_route(
    descriptions: list[Any],
    system_ids: list[str],
    system_domains: list[str],
    known_domains: set[str],
) -> tuple[str, list[str], str, str, list[str], str]:
    text = normalize_description_text(descriptions)
    rules: tuple[
        tuple[str, str, tuple[str, ...], tuple[str, ...]], ...
    ] = (
        (
            "LEX_TURBOCHARGER",
            "turbocharger_rotating_hot_flow_assembly",
            (" turbocharger ", " turbo charger "),
            ("powertrain_0d", "rotordynamics", "structural", "thermal_fluid"),
        ),
        (
            "LEX_BRAKE_FRICTION_HYDRAULIC",
            "brake_hydraulic_friction_component",
            (
                " brake ", " caliper ", " calliper ", " brake disc ",
                " master cylinder ", " brake booster ", " booster ",
            ),
            ("hydraulic_0d", "structural", "thermal_fluid", "vehicle_dynamics"),
        ),
        (
            "LEX_GLAZING_OPTICAL",
            "glazing_mirror_or_optical_component",
            (
                " rear window ", " windshield ", " windscreen ",
                " window pane ", " mirror glass ", " lens ",
            ),
            ("external_aero", "package_interfaces", "structural"),
        ),
        (
            "LEX_INSTRUMENT_GAUGE_DISPLAY",
            "instrument_gauge_or_display_component",
            (
                " speedometer ", " tachometer ", " instrument cluster ",
                " gauge ", " clock ", " odometer ", " display ",
            ),
            ("controls", "electrical_network", "package_interfaces"),
        ),
        (
            "LEX_ELASTOMER_MOUNT_BUFFER",
            "elastomer_mount_buffer_or_grommet",
            (
                " rubber sleeve ", " grommet ", " rubber mounting ",
                " rubber mount ", " bonded rubber buffer ", " rubber pad ",
                " rubber block ", " buffer ", " stopper ",
            ),
            ("multibody", "package_interfaces", "structural"),
        ),
        (
            "LEX_SHIM_SPACER_ALIGNMENT",
            "shim_spacer_or_alignment_component",
            (
                " adjusting shim ", " shim ", " spacer ",
                " distance piece ", " adjusting ring ", " spacer sleeve ",
                " dowel sleeve ",
            ),
            ("package_interfaces", "structural"),
        ),
        (
            "LEX_SEAL_GASKET_BOOT",
            "seal_gasket_or_boot",
            (
                " seal ", " gasket ", " o ring ", " sealing ring ",
                " sealing strip ", " sealing frame ", " bellows ",
                " joint rubber ", " boot ",
            ),
            ("network_flow", "package_interfaces", "thermal_fluid"),
        ),
        (
            "LEX_WHEEL_SUSPENSION_STEERING",
            "wheel_suspension_or_steering_component",
            (
                " wheel ", " steering ", " strut ", " shock absorber ",
                " control arm ", " trailing arm ", " stabilizer ", " tie rod ",
                " stabiliser ", " wishbone ", " wheel hub ", " wheel carrier ",
                " track rod ", " axle carrier ",
            ),
            ("multibody", "package_interfaces", "structural", "vehicle_dynamics"),
        ),
        (
            "LEX_BEARING_BUSHING",
            "bearing_or_bushing",
            (" bearing ", " bushing ", " bush ", " needle cage "),
            ("multibody", "rotordynamics", "structural"),
        ),
        (
            "LEX_HOUSING_CASE_MANIFOLD",
            "housing_case_or_manifold",
            (
                " housing ", " transmission case ", " gear case ",
                " crankcase ", " manifold ", " distributor housing ",
            ),
            ("network_flow", "package_interfaces", "structural", "thermal_fluid"),
        ),
        (
            "LEX_LINKAGE_LEVER_CABLE_CONTROL",
            "linkage_lever_cable_or_control",
            (
                " lever ", " accelerator cable ", " bowden cable ",
                " cable ", " push rod ", " pull rod ", " shift fork ",
                " pedal ", " throttle linkage ",
            ),
            ("controls", "multibody", "package_interfaces", "structural"),
        ),
        (
            "LEX_GUIDE_RAIL_SLIDE_HINGE",
            "guide_rail_slide_or_hinge",
            (
                " gate guide ", " guide rail ", " guide ", " rail ",
                " slide ", " hinge ",
            ),
            ("multibody", "package_interfaces", "structural"),
        ),
        (
            "LEX_FILTER_SCREEN_FLOW_CONDITIONER",
            "filter_screen_or_flow_conditioner",
            (
                " air cleaner ", " oil filter ", " filter ", " screen ",
                " nozzle ", " vanes ", " intake trumpet ",
            ),
            ("network_flow", "package_interfaces", "thermal_fluid"),
        ),
        (
            "LEX_INSULATION_ABSORBER_HEAT_SHIELD",
            "insulation_absorber_or_heat_shield",
            (
                " sound absorber ", " heat protection ", " protective plate ",
                " heat shield ", " insulation ", " damping plate ",
            ),
            ("package_interfaces", "thermal_cabin", "thermal_fluid"),
        ),
        (
            "LEX_ELECTRICAL_SENSOR_ACTUATOR",
            "sensor_actuator_or_electrical_component",
            (
                " sensor ", " switch ", " relay ", " wiring ", " wire ",
                " harness ", " lamp ", " headlamp ", " bulb ", " motor ",
                " control unit ", " ignition lead ", " spark plug connector ",
                " microswitch ", " loudspeaker ", " radio ", " fanfare ",
                " combined lights ", " direction indicator ", " plug socket ",
                " connecting cable ", " handheld transmitter ", " wiper arm ",
                " wiper blade ",
            ),
            ("controls", "electrical_network", "package_interfaces"),
        ),
        (
            "LEX_FLUID_HOSE_PIPE_DUCT",
            "fluid_hose_pipe_or_duct",
            (
                " hose ", " pressure line ", " pressure pipe ", " fuel line ",
                " oil line ", " return line ", " vent line ",
                " refrigerant line ", " connecting line ", " piping ",
                " pipe ", " tube ", " duct ", " air guide ",
                " hot air socket ",
            ),
            ("network_flow", "package_interfaces", "thermal_fluid"),
        ),
        (
            "LEX_HEAT_EXCHANGER_COOLER",
            "heat_exchanger_or_cooler",
            (" heat exchanger ", " cooler ", " intercooler ", " radiator "),
            ("network_flow", "structural", "thermal_fluid"),
        ),
        (
            "LEX_PUMP_VALVE_INJECTOR",
            "pump_valve_or_injector",
            (
                " pump ", " valve ", " injector ", " regulator ",
                " thermostat ", " pressure accumulator ",
            ),
            ("network_flow", "powertrain_0d", "structural", "thermal_fluid"),
        ),
        (
            "LEX_ROTATING_POWERTRAIN",
            "rotating_powertrain_component",
            (
                " crankshaft ", " camshaft ", " connecting rod ", " piston ",
                " flywheel ", " clutch ", " gear ", " shaft ", " sprocket ",
                " transmission ", " differential ", " synchroniser ",
                " synchronizer ", " pulley ", " rocker arm ", " axle shaft ",
            ),
            ("multibody", "powertrain_0d", "rotordynamics", "structural"),
        ),
        (
            "LEX_LOAD_BEARING_BRACKET_MOUNT",
            "load_bearing_bracket_carrier_or_mount",
            (
                " carrier ", " bracket ", " support ", " crossmember ",
                " cross member ", " subframe ", " engine mount ",
                " mounting plate ", " supporting mount ", " gusset plate ",
                " fastening angle ",
            ),
            ("multibody", "package_interfaces", "structural"),
        ),
        (
            "LEX_SPRING_BELT_COMPLIANT",
            "spring_belt_or_compliant_mechanism",
            (" spring ", " belt ", " tensioner ", " damper "),
            ("multibody", "structural"),
        ),
        (
            "LEX_STRUCTURAL_REINFORCEMENT",
            "structural_reinforcement_member_or_plate",
            (
                " reinforcement ", " side member ", " rear bulkhead ",
                " bulkhead ", " side section ", " joining plate ",
            ),
            ("crash", "package_interfaces", "structural"),
        ),
        (
            "LEX_BODY_PANEL_EXTERNAL_STRUCTURE",
            "body_panel_or_external_structure",
            (
                " body ", " door ", " roof ", " fender ", " bonnet ",
                " lid ", " bumper ", " spoiler ", " wing ",
                " windscreen frame ", " hinge pillar ",
            ),
            ("crash", "external_aero", "package_interfaces", "structural"),
        ),
        (
            "LEX_SEAT_RESTRAINT_OCCUPANT",
            "seat_restraint_or_occupant_structure",
            (" seat ", " safety belt ", " restraint ", " airbag "),
            ("crash", "package_interfaces", "structural"),
        ),
        (
            "LEX_HVAC_CABIN_THERMAL",
            "hvac_or_cabin_thermal_component",
            (
                " heater ", " evaporator ", " air conditioning ",
                " ventilation ", " blower ",
            ),
            ("controls", "network_flow", "thermal_cabin"),
        ),
        (
            "LEX_FUEL_EXHAUST_EMISSIONS",
            "fuel_exhaust_or_emissions_component",
            (
                " fuel tank ", " muffler ", " silencer ", " exhaust ",
                " catalytic converter ", " catalyst ",
            ),
            ("network_flow", "structural", "thermal_fluid"),
        ),
        (
            "LEX_JOINT_COUPLING_FLANGE",
            "joint_coupling_or_flange",
            (" joint ", " flange ", " coupling ", " universal joint "),
            ("multibody", "package_interfaces", "structural"),
        ),
        (
            "LEX_FASTENER_RETAINER",
            "fastener_or_retainer",
            (
                " bolt ", " screw ", " nut ", " washer ", " stud ",
                " rivet ", " circlip ", " retaining ring ", " clamp ",
                " clip ", " roll pin ", " straight pin ", " pin ",
            ),
            ("package_interfaces", "structural"),
        ),
        (
            "LEX_SERVICE_MATERIAL_KIT",
            "service_material_chemical_or_kit",
            (
                " loctite ", " sealing compound ", " adhesive ", " grease ",
                " repair kit ", " package box ",
            ),
            ("materials_and_process", "package_interfaces"),
        ),
        (
            "LEX_LABEL_DECAL_FILM_TRIM",
            "label_decal_film_or_trim_item",
            (
                " sticker ", " label ", " decal ", " stone guard film ",
                " logo ", " rosette ", " moulding ",
                " knee protection strip ", " sun visor ",
            ),
            ("package_interfaces",),
        ),
        (
            "LEX_COVER_CAP_TRIM",
            "cover_cap_or_trim",
            (
                " cover ", " cap ", " trim ", " panel ", " carpet ",
                " lining ", " grille ", " knob ", " centre console ",
                " center console ",
            ),
            ("package_interfaces",),
        ),
        (
            "LEX_GENERIC_RIGID_INTERFACE",
            "generic_rigid_interface_piece",
            (
                " connection piece ", " connecting piece ",
                " intermediate piece ", " distributing piece ",
                " mounting piece ", " end piece ", " filler piece ",
                " threaded plate ", " sleeve ", " insert ", " plate ",
            ),
            ("package_interfaces", "structural"),
        ),
    )
    for rule_id, archetype, terms, domain_ids in rules:
        matched_terms = sorted(term.strip() for term in terms if term in text)
        if matched_terms:
            unknown = set(domain_ids) - known_domains
            if unknown:
                raise ContractError(
                    f"archetype_unknown_domains:{archetype}:{sorted(unknown)}"
                )
            return (
                archetype,
                sorted(domain_ids),
                "description_keyword_hypothesis_requires_engineering_review",
                rule_id,
                matched_terms,
                "lexical_candidate_not_human_reviewed",
            )
    system_fallbacks = {
        "0xx": "generic_system_0xx_service_or_documentation",
        "1xx": "generic_system_1xx_engine_component",
        "2xx": "generic_system_2xx_fuel_exhaust_component",
        "3xx": "generic_system_3xx_transmission_component",
        "4xx": "generic_system_4xx_front_axle_steering_component",
        "5xx": "generic_system_5xx_rear_axle_driveline_component",
        "6xx": "generic_system_6xx_brake_hydraulic_component",
        "7xx": "generic_system_7xx_controls_pedals_clutch_component",
        "8xx": "generic_system_8xx_body_cabin_electrical_component",
        "9xx": "generic_system_9xx_option_accessory_component",
    }
    if not system_ids:
        raise ContractError("archetype_route_without_system")
    primary_system_id = sorted(system_ids)[0]
    if primary_system_id not in system_fallbacks:
        raise ContractError(f"archetype_unknown_primary_system:{primary_system_id}")
    return (
        system_fallbacks[primary_system_id],
        sorted(system_domains),
        "system_context_fallback_requires_description_or_geometry_review",
        f"SYSTEM_FALLBACK_{primary_system_id.upper()}",
        [],
        "system_context_only_not_part_classification",
    )


def declared_evidence(master: dict[str, Any]) -> dict[str, Any]:
    observations = master.get("documentary_graph", {}).get("declared_engineering_observations", [])
    observations = observations if isinstance(observations, list) else []
    bounding_boxes = [
        item.get("bounding_box_mm")
        for item in observations
        if isinstance(item, dict)
        and isinstance(item.get("bounding_box_mm"), list)
        and len(item["bounding_box_mm"]) == 3
    ]
    masses = [
        item.get("mass_kg")
        for item in observations
        if isinstance(item, dict) and isinstance(item.get("mass_kg"), (int, float))
    ]
    materials = [
        item.get("material")
        for item in observations
        if isinstance(item, dict)
        and isinstance(item.get("material"), str)
        and item["material"].strip().lower() not in PLACEHOLDER_MATERIALS
    ]
    return {
        "declared_observation_count": len(observations),
        "declared_bounding_box_count": len(bounding_boxes),
        "declared_mass_count": len(masses),
        "non_placeholder_declared_material_count": len(materials),
        "declared_bounding_boxes_mm": bounding_boxes,
        "declared_masses_kg": masses,
        "declared_material_labels": materials,
        "qualified_material_decision": False,
    }


def build_configuration_maps(
    roster: dict[str, Any],
    part_links: dict[str, Any],
    exceptions: dict[str, Any],
) -> tuple[
    dict[str, set[str]],
    dict[str, set[str]],
    dict[str, set[str]],
    set[str],
]:
    candidate_by_id = {
        str(item["configuration_candidate_id"]): item
        for item in roster.get("configuration_candidates", [])
        if isinstance(item, dict) and item.get("configuration_candidate_id")
    }
    turbo_candidate_ids = {
        candidate_id
        for candidate_id, item in candidate_by_id.items()
        if item.get("model_family") == "turbo"
    }
    configuration_ids_by_master: dict[str, set[str]] = defaultdict(set)
    occurrence_ids_by_master: dict[str, set[str]] = defaultdict(set)
    for link in part_links.get("resolved_constraint_links", []):
        if not isinstance(link, dict):
            continue
        master_id = link.get("part_master_twin_id")
        occurrence_id = link.get("occurrence_twin_id")
        candidate_ids = link.get("compatible_configuration_candidate_ids")
        if not isinstance(master_id, str) or not isinstance(candidate_ids, list):
            raise ContractError("resolved_part_link_record")
        unknown = {str(value) for value in candidate_ids} - set(candidate_by_id)
        if unknown:
            raise ContractError(f"unknown_configuration_candidates:{sorted(unknown)[:3]}")
        configuration_ids_by_master[master_id].update(str(value) for value in candidate_ids)
        if isinstance(occurrence_id, str):
            occurrence_ids_by_master[master_id].add(occurrence_id)
    exception_ids_by_master: dict[str, set[str]] = defaultdict(set)
    for mapping in exceptions.get("exception_occurrence_mappings", []):
        if not isinstance(mapping, dict):
            continue
        master_id = mapping.get("part_master_twin_id")
        contract_id = mapping.get("exception_contract_id")
        occurrence_id = mapping.get("occurrence_twin_id")
        if not isinstance(master_id, str) or not isinstance(contract_id, str):
            raise ContractError("exception_mapping_record")
        exception_ids_by_master[master_id].add(contract_id)
        if isinstance(occurrence_id, str):
            occurrence_ids_by_master[master_id].add(occurrence_id)
    return (
        configuration_ids_by_master,
        exception_ids_by_master,
        occurrence_ids_by_master,
        turbo_candidate_ids,
    )


def build_manual_evidence_map(
    manual_routing: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in manual_routing.get("part_review_candidates", []):
        if not isinstance(candidate, dict):
            raise ContractError("manual_part_review_candidate")
        master_ids = candidate.get("candidate_part_master_twin_ids")
        if not isinstance(master_ids, list) or not master_ids:
            raise ContractError("manual_candidate_master_ids")
        summary = {
            "manual_evidence_id": candidate.get("manual_evidence_id"),
            "source_collection": candidate.get("source_collection"),
            "source_index": candidate.get("source_index"),
            "pdf_page": candidate.get("pdf_page"),
            "system_id": candidate.get("system_id"),
            "matched_description_phrases": candidate.get(
                "matched_description_phrases", []
            ),
            "candidate_part_master_count": candidate.get(
                "candidate_part_master_count"
            ),
            "lexically_unambiguous": candidate.get("lexically_unambiguous"),
            "review_status": candidate.get("review_status"),
        }
        for master_id in master_ids:
            if not isinstance(master_id, str):
                raise ContractError("manual_candidate_master_id")
            result[master_id].append(summary)
    for candidates in result.values():
        candidates.sort(key=lambda item: str(item["manual_evidence_id"]))
    return result


def build_catalog_engineering_map(
    crosswalk: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[str, set[str]] = defaultdict(set)
    for entry in crosswalk.get("parts", []):
        if not isinstance(entry, dict):
            raise ContractError("catalog_crosswalk_part")
        part_record = entry.get("part_record")
        part_id = entry.get("part_id")
        if not isinstance(part_record, str) or not isinstance(part_id, str):
            raise ContractError("catalog_crosswalk_part_record")
        matches = entry.get("pet_occurrence_matches", [])
        if not isinstance(matches, list):
            raise ContractError("catalog_crosswalk_matches")
        if not matches:
            continue
        part = load_json(ROOT / part_record)
        summary = {
            "part_id": part_id,
            "part_record": part_record,
            "crosswalk_status": entry.get("status"),
            "name": part.get("name"),
            "classification": part.get("classification", {}),
            "geometry": {
                "source_type": part.get("geometry", {}).get("source_type"),
                "master_format": part.get("geometry", {}).get("master_format"),
                "master_file": part.get("geometry", {}).get("master_file"),
                "accuracy_mm": part.get("geometry", {}).get("accuracy_mm"),
            },
            "manufacturing_hypotheses": {
                "candidate_processes": part.get("manufacturing", {}).get(
                    "candidate_processes", []
                ),
                "preferred_process": part.get("manufacturing", {}).get(
                    "preferred_process"
                ),
                "material": part.get("manufacturing", {}).get("material", {}),
            },
            "validation": {
                "status": part.get("validation", {}).get("status"),
                "reviewed_by": part.get("validation", {}).get("reviewed_by"),
                "reviewed_on": part.get("validation", {}).get("reviewed_on"),
                "evidence_count": len(part.get("validation", {}).get("evidence", [])),
                "known_limit_count": len(
                    part.get("validation", {}).get("known_limits", [])
                ),
            },
            "engineering_status": "linked_catalog_record_hypotheses_not_qualified_decisions",
        }
        for match in matches:
            if not isinstance(match, dict):
                raise ContractError("catalog_crosswalk_match")
            master_id = match.get("part_master_twin_id")
            if not isinstance(master_id, str):
                raise ContractError("catalog_crosswalk_master_id")
            if part_id in seen[master_id]:
                continue
            seen[master_id].add(part_id)
            result[master_id].append(summary)
    for records in result.values():
        records.sort(key=lambda item: str(item["part_id"]))
    return result


def build_simulation_evidence_map(
    contract: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in contract.get("links", []):
        if not isinstance(link, dict):
            raise ContractError("engineering_evidence_link")
        part_id = link.get("part_id")
        master_ids = link.get("pet_part_master_twin_ids")
        if not isinstance(part_id, str) or not isinstance(master_ids, list):
            raise ContractError("engineering_evidence_link_identity")
        catalogue_contracts = link.get("catalogue_twin_contracts", [])
        component_contracts = link.get("engine_component_contracts", [])
        engine_cases = link.get("engine_load_case_contracts", [])
        virtual_f2 = link.get("virtual_F2_readiness_contract")
        valve_surrogate = link.get("valve_dimensional_surrogate_contract")
        k16_surrogate = link.get("k16_envelope_flow_surrogate_contract")
        if not all(
            isinstance(value, list)
            for value in (catalogue_contracts, component_contracts, engine_cases)
        ):
            raise ContractError("engineering_evidence_link_records")
        if virtual_f2 is not None and not isinstance(virtual_f2, dict):
            raise ContractError("virtual_F2_readiness_record")
        if valve_surrogate is not None and not isinstance(valve_surrogate, dict):
            raise ContractError("valve_dimensional_surrogate_record")
        if k16_surrogate is not None and not isinstance(k16_surrogate, dict):
            raise ContractError("k16_envelope_flow_surrogate_record")
        load_cases = [
            {
                "load_case_id": case.get("load_case_id"),
                "kind": case.get("kind"),
                "status": case.get("status"),
                "required_input_ids": sorted(case.get("required_inputs", {})),
            }
            for case in engine_cases
            if isinstance(case, dict)
        ]
        for record in catalogue_contracts:
            if not isinstance(record, dict):
                raise ContractError("catalogue_twin_evidence_record")
            load_cases.extend(
                {
                    "load_case_id": case_id,
                    "kind": "catalogue_twin_domain_specific_case",
                    "status": status,
                    "required_input_ids": [],
                }
                for case_id, status in zip(
                    record.get("load_case_ids", []),
                    record.get("load_case_statuses", []),
                    strict=True,
                )
            )
        summary = {
            "part_id": part_id,
            "evidence_status": link.get("evidence_status"),
            "catalogue_twin_ids": sorted(
                str(record["twin_id"])
                for record in catalogue_contracts
                if isinstance(record, dict) and isinstance(record.get("twin_id"), str)
            ),
            "engine_component_ids": sorted(
                str(record["component_id"])
                for record in component_contracts
                if isinstance(record, dict)
                and isinstance(record.get("component_id"), str)
            ),
            "load_cases": sorted(
                load_cases, key=lambda item: str(item.get("load_case_id"))
            ),
            "virtual_F2_readiness_contract": virtual_f2,
            "valve_dimensional_surrogate_contract": valve_surrogate,
            "k16_envelope_flow_surrogate_contract": k16_surrogate,
            "charge_air_chain_surrogate_contract": None,
            "heat_shield_thermal_surrogate_contract": None,
            "turbo_lubrication_control_topology_contract": None,
            "oil_tank_circuit_topology_contract": None,
            "oil_cooler_circuit_topology_contract": None,
            "analysis_geometry_available": False,
            "reference_solver_results_promoted": 0,
            "physicsnemo_results_promoted": 0,
            "simready_or_manufacturing_release_promoted": 0,
        }
        for master_id in master_ids:
            if not isinstance(master_id, str):
                raise ContractError("engineering_evidence_master_id")
            result[master_id].append(summary)
    for link in contract.get("declared_reference_links", []):
        if not isinstance(link, dict):
            raise ContractError("declared_reference_evidence_link")
        evidence_id = link.get("evidence_id")
        master_ids = link.get("pet_part_master_twin_ids")
        charge_air_surrogate = link.get("charge_air_chain_surrogate_contract")
        heat_shield_surrogate = link.get("heat_shield_thermal_surrogate_contract")
        turbo_lubrication_control = link.get(
            "turbo_lubrication_control_topology_contract"
        )
        oil_tank_circuit = link.get("oil_tank_circuit_topology_contract")
        oil_cooler_circuit = link.get("oil_cooler_circuit_topology_contract")
        if (
            not isinstance(evidence_id, str)
            or not isinstance(master_ids, list)
            or sum(
                isinstance(value, dict)
                for value in (
                    charge_air_surrogate,
                    heat_shield_surrogate,
                    turbo_lubrication_control,
                    oil_tank_circuit,
                    oil_cooler_circuit,
                )
            )
            != 1
        ):
            raise ContractError("declared_reference_evidence_link_identity")
        summary = {
            "part_id": None,
            "evidence_id": evidence_id,
            "evidence_status": link.get("evidence_status"),
            "catalogue_twin_ids": [],
            "engine_component_ids": [],
            "load_cases": [],
            "virtual_F2_readiness_contract": None,
            "valve_dimensional_surrogate_contract": None,
            "k16_envelope_flow_surrogate_contract": None,
            "charge_air_chain_surrogate_contract": charge_air_surrogate,
            "heat_shield_thermal_surrogate_contract": heat_shield_surrogate,
            "turbo_lubrication_control_topology_contract": (
                turbo_lubrication_control
            ),
            "oil_tank_circuit_topology_contract": oil_tank_circuit,
            "oil_cooler_circuit_topology_contract": oil_cooler_circuit,
            "analysis_geometry_available": False,
            "reference_solver_results_promoted": 0,
            "physicsnemo_results_promoted": 0,
            "simready_or_manufacturing_release_promoted": 0,
        }
        for master_id in master_ids:
            if not isinstance(master_id, str):
                raise ContractError("declared_reference_evidence_master_id")
            result[master_id].append(summary)
    for records in result.values():
        records.sort(
            key=lambda item: str(item.get("part_id") or item.get("evidence_id"))
        )
    return result


def task_priority(
    *,
    turbo_evidence: bool,
    has_configuration_evidence: bool,
    tier: str,
    has_declared_geometry: bool,
) -> tuple[str, int, list[str]]:
    reasons: list[str] = []
    if turbo_evidence:
        reasons.append("first_integration_target_turbo_applicability")
        return "P0", 0, reasons
    if has_configuration_evidence and tier == "safety_critical":
        reasons.append("configuration_evidence_and_safety_critical_system")
        if has_declared_geometry:
            reasons.append("declared_geometry_available_for_review")
        return "P1", 10, reasons
    if has_configuration_evidence:
        reasons.append("configuration_evidence_available")
        return "P2", 20, reasons
    if tier == "safety_critical":
        reasons.append("safety_critical_system_without_configuration_resolution")
        return "P3", 30, reasons
    reasons.append("documentary_identity_only")
    return "P4", 40, reasons


def build_task(
    master: dict[str, Any],
    *,
    routes: dict[str, dict[str, Any]],
    configuration_ids: set[str],
    exception_ids: set[str],
    constraint_occurrence_ids: set[str],
    turbo_candidate_ids: set[str],
    domain_contracts: dict[str, dict[str, Any]],
    physicsnemo_policy: dict[str, Any],
    manual_evidence_candidates: list[dict[str, Any]],
    catalog_engineering_records: list[dict[str, Any]],
    simulation_evidence_records: list[dict[str, Any]],
    catalogue_proxy_records: list[dict[str, Any]],
) -> dict[str, Any]:
    master_id = str(master["twin_id"])
    documentary = master.get("documentary_graph", {})
    system_ids = sorted(
        str(value) for value in documentary.get("system_ids", []) if str(value) in routes
    )
    if not system_ids:
        raise ContractError(f"master_without_system:{master_id}")
    criticalities = {str(routes[system_id]["criticality"]) for system_id in system_ids}
    system_candidate_domains = sorted(
        {
            str(domain)
            for system_id in system_ids
            for domain in routes[system_id]["simulation_domain_ids"]
        }
    )
    subject = master.get("subject", {})
    (
        archetype,
        simulation_domains,
        domain_routing_status,
        classification_rule_id,
        matched_description_terms,
        classification_confidence,
    ) = engineering_archetype_route(
        subject.get("descriptions", []),
        system_ids,
        system_candidate_domains,
        set(domain_contracts),
    )
    unknown_domains = set(simulation_domains) - set(domain_contracts)
    if unknown_domains:
        raise ContractError(f"unknown_simulation_domains:{master_id}:{sorted(unknown_domains)}")
    physicsnemo_candidates = sorted(
        {
            str(model)
            for domain_id in simulation_domains
            for model in domain_contracts[domain_id]["physicsnemo_candidates"]
        }
    )
    tier = criticality_tier(criticalities)
    evidence = declared_evidence(master)
    proven_variant_contexts = documentary.get("proven_variant_contexts", [])
    proven_variant_contexts = (
        proven_variant_contexts if isinstance(proven_variant_contexts, list) else []
    )
    proven_variants = sorted(
        {
            str(value)
            for context in proven_variant_contexts
            if isinstance(context, dict)
            for value in context.get("proven_variants", [])
            if isinstance(value, str)
        }
    )
    has_configuration_evidence = bool(configuration_ids or exception_ids or proven_variants)
    turbo_evidence = bool(configuration_ids.intersection(turbo_candidate_ids)) or bool(
        {"CONFIG-EXCEPTION-993-TURBO-S"}.intersection(exception_ids)
    ) or bool({"993-turbo", "993-turbo-s"}.intersection(proven_variants))
    priority, priority_score, priority_reasons = task_priority(
        turbo_evidence=turbo_evidence,
        has_configuration_evidence=has_configuration_evidence,
        tier=tier,
        has_declared_geometry=evidence["declared_bounding_box_count"] > 0,
    )
    has_valve_dimensional_surrogate = any(
        record.get("valve_dimensional_surrogate_contract") is not None
        for record in simulation_evidence_records
    )
    has_k16_envelope_flow_surrogate = any(
        record.get("k16_envelope_flow_surrogate_contract") is not None
        for record in simulation_evidence_records
    )
    has_charge_air_chain_surrogate = any(
        record.get("charge_air_chain_surrogate_contract") is not None
        for record in simulation_evidence_records
    )
    has_heat_shield_thermal_surrogate = any(
        record.get("heat_shield_thermal_surrogate_contract") is not None
        for record in simulation_evidence_records
    )
    has_turbo_lubrication_control_topology = any(
        record.get("turbo_lubrication_control_topology_contract") is not None
        for record in simulation_evidence_records
    )
    has_oil_tank_circuit_topology = any(
        record.get("oil_tank_circuit_topology_contract") is not None
        for record in simulation_evidence_records
    )
    has_oil_cooler_circuit_topology = any(
        record.get("oil_cooler_circuit_topology_contract") is not None
        for record in simulation_evidence_records
    )
    has_virtual_f2_readiness = any(
        record.get("virtual_F2_readiness_contract") is not None
        for record in simulation_evidence_records
    )
    if not has_configuration_evidence:
        next_gate = "resolve_configuration_applicability"
    elif has_k16_envelope_flow_surrogate:
        next_gate = "replace_F1_k16_guides_with_F2_interfaces_and_F3_flowpath"
    elif has_charge_air_chain_surrogate:
        next_gate = "replace_F1_charge_air_guides_with_F2_interfaces_and_F3_flow_domains"
    elif has_heat_shield_thermal_surrogate:
        next_gate = "replace_F1_heat_shield_envelope_with_F2_surface_mount_gap_and_clearance_geometry"
    elif has_turbo_lubrication_control_topology:
        next_gate = "resolve_202_16_configuration_topology_side_assignment_and_F2_interfaces"
    elif has_oil_tank_circuit_topology:
        next_gate = "resolve_104_01_configuration_topology_F2_interfaces_and_oil_properties"
    elif has_oil_cooler_circuit_topology:
        next_gate = "resolve_104_05_configuration_topology_F2_interfaces_oil_air_properties_and_fan_control"
    elif has_virtual_f2_readiness:
        next_gate = "infer_and_cross_check_F2_interface_coordinates_with_uncertainty"
    elif catalogue_proxy_records:
        next_gate = "replace_F1_envelope_with_F2_interface_geometry"
    elif has_valve_dimensional_surrogate:
        next_gate = "replace_F1_valve_surrogate_with_F2_interface_geometry"
    else:
        next_gate = "author_editable_geometry_and_measured_interfaces"
    required_actions = [next_gate]
    if manual_evidence_candidates:
        required_actions.append("review_workshop_manual_evidence_candidates")
    if catalog_engineering_records:
        required_actions.append("review_linked_catalog_part_engineering_records")
    if simulation_evidence_records:
        required_actions.append("review_linked_simulation_contracts")
    if catalogue_proxy_records:
        required_actions.append(
            "review_F1_envelope_sources_and_replace_with_interface_geometry"
        )
    if has_valve_dimensional_surrogate:
        required_actions.append(
            "review_F1_valve_dimensions_and_replace_profile_hypotheses_with_interfaces"
        )
    if has_k16_envelope_flow_surrogate:
        required_actions.append(
            "review_K16_envelopes_right_diameter_evidence_and_symbolic_zeroD_contracts"
        )
    if has_charge_air_chain_surrogate:
        required_actions.append(
            "review_charge_air_envelopes_quarantined_dimensions_and_symbolic_zeroD_contracts"
        )
    if has_heat_shield_thermal_surrogate:
        required_actions.append(
            "review_heat_shield_envelope_mass_symbolic_thermal_contract_and_material_screening"
        )
    if has_turbo_lubrication_control_topology:
        required_actions.append(
            "review_202_16_nonspatial_topology_roles_connections_equations_and_unknowns"
        )
    if has_oil_tank_circuit_topology:
        required_actions.append(
            "review_104_01_nonspatial_oil_tank_topology_roles_connections_equations_and_unknowns"
        )
    if has_oil_cooler_circuit_topology:
        required_actions.append(
            "review_104_05_nonspatial_oil_cooler_topology_roles_connections_equations_and_unknowns"
        )
    if has_virtual_f2_readiness:
        required_actions.append(
            "review_mass_constrained_surrogate_interface_hypotheses_and_virtual_F2_parameters"
        )
    required_actions.extend(
        [
            "identify_interfaces_tolerances_material_and_original_process",
            "define_load_cases_boundary_conditions_and_acceptance_criteria",
            "run_converged_reference_solver_before_any_physicsnemo_surrogate",
            "assemble_validated_geometry_in_omniverse_after_usd_preflight",
        ]
    )
    normalized_reference = subject.get("normalized_oem_reference")
    if not isinstance(normalized_reference, str) or not normalized_reference:
        raise ContractError(f"master_normalized_reference:{master_id}")
    return {
        "schema_version": "1.0.0",
        "engineering_task_id": f"ENG-PET-993-{sha256_text(master_id)[:20].upper()}",
        "part_master_twin_id": master_id,
        "subject": {
            "normalized_oem_reference": normalized_reference,
            "display_references": subject.get("display_references", []),
            "descriptions": subject.get("descriptions", []),
        },
        "documentary_scope": {
            "occurrence_count": documentary.get("occurrence_count"),
            "system_ids": system_ids,
            "pet_illustrations": documentary.get("pet_illustrations", []),
            "recorded_source_material_observation_count": len(
                documentary.get("source_material_observations", [])
            ),
            "recorded_source_safety_observation_count": len(
                documentary.get("source_safety_observations", [])
            ),
        },
        "configuration_evidence": {
            "status": (
                "candidate_or_exception_constraints_available"
                if has_configuration_evidence
                else "unresolved_catalogue_identity_only"
            ),
            "single_dimension_constraint_occurrence_ids": sorted(constraint_occurrence_ids),
            "compatible_configuration_candidate_count": len(configuration_ids),
            "compatible_configuration_candidate_ids": sorted(configuration_ids),
            "exception_contract_ids": sorted(exception_ids),
            "human_read_proven_variants": proven_variants,
            "turbo_integration_evidence": turbo_evidence,
            "configured_vehicle_bom_membership": False,
        },
        "risk_and_priority": {
            "criticality_tier": tier,
            "program_criticalities": sorted(criticalities),
            "priority": priority,
            "priority_score": priority_score,
            "priority_reasons": priority_reasons,
            "professional_engineering_review_required": True,
        },
        "input_evidence": evidence,
        "workshop_manual_evidence": {
            "status": (
                "review_candidates_available_not_assigned"
                if manual_evidence_candidates
                else "no_exact_lexical_candidate"
            ),
            "candidate_record_count": len(manual_evidence_candidates),
            "candidates": manual_evidence_candidates,
            "promoted_measurements_or_torques": 0,
            "manual_review_completed": False,
        },
        "catalog_part_engineering": {
            "status": (
                "linked_hypotheses_available_not_qualified"
                if catalog_engineering_records
                else "no_linked_catalog_part_record"
            ),
            "record_count": len(catalog_engineering_records),
            "records": catalog_engineering_records,
            "material_or_process_decisions_promoted": 0,
            "geometry_or_validation_claims_promoted": 0,
        },
        "linked_simulation_evidence": {
            "status": (
                "blocked_contracts_available_for_input_review"
                if simulation_evidence_records
                else "no_linked_simulation_contract"
            ),
            "record_count": len(simulation_evidence_records),
            "records": simulation_evidence_records,
            "reference_solver_results_promoted": 0,
            "physicsnemo_results_promoted": 0,
            "simready_or_manufacturing_release_promoted": 0,
        },
        "catalogue_proxy_geometry": {
            "status": (
                "F1_envelope_candidates_linked_by_exact_oem_identity"
                if catalogue_proxy_records
                else "no_exact_oem_proxy_candidate"
            ),
            "record_count": len(catalogue_proxy_records),
            "records": catalogue_proxy_records,
            "geometry_composed_into_vehicle": False,
            "vehicle_transform_known": False,
            "interface_geometry_available": False,
            "dimensionally_accurate_claim": False,
            "fitment_validated_claim": False,
        },
        "engineering_gates": {
            "current_fidelity": (
                "F1_k16_envelope_diameter_guides_unvalidated"
                if has_k16_envelope_flow_surrogate
                else "F1_charge_air_chain_guides_unvalidated"
                if has_charge_air_chain_surrogate
                else "F1_heat_shield_envelope_thermal_readiness_unvalidated"
                if has_heat_shield_thermal_surrogate
                else "F1_turbo_lubrication_control_topology_readiness_unvalidated"
                if has_turbo_lubrication_control_topology
                else "F1_oil_tank_circuit_topology_readiness_unvalidated"
                if has_oil_tank_circuit_topology
                else "F1_oil_cooler_circuit_topology_readiness_unvalidated"
                if has_oil_cooler_circuit_topology
                else "F1_mass_constrained_structural_surrogate_virtual_F2_readiness"
                if has_virtual_f2_readiness
                else "F1_envelope_identity_linked_unvalidated"
                if catalogue_proxy_records
                else "F1_valve_dimensional_surrogate_unvalidated"
                if has_valve_dimensional_surrogate
                else master.get("engineering_state", {}).get(
                    "fidelity", "F0_reference"
                )
            ),
            "identity_master": (
                "pass_documentary_plus_exact_K16_surrogate_identity"
                if has_k16_envelope_flow_surrogate
                else "pass_documentary_plus_exact_charge_air_surrogate_identity"
                if has_charge_air_chain_surrogate
                else "pass_documentary_plus_exact_heat_shield_thermal_surrogate_identity"
                if has_heat_shield_thermal_surrogate
                else "pass_documentary_plus_exact_202_16_topology_identity"
                if has_turbo_lubrication_control_topology
                else "pass_documentary_plus_exact_104_01_oil_tank_topology_identity"
                if has_oil_tank_circuit_topology
                else "pass_documentary_plus_exact_104_05_oil_cooler_topology_identity"
                if has_oil_cooler_circuit_topology
                else "pass_documentary_plus_virtual_F2_readiness_identity"
                if has_virtual_f2_readiness
                else "pass_documentary_plus_exact_proxy_identity_candidate"
                if catalogue_proxy_records
                else "pass_documentary_plus_exact_valve_surrogate_identity"
                if has_valve_dimensional_surrogate
                else "pass_documentary_only"
            ),
            "configuration_applicability": (
                "candidate_constraints_not_bom"
                if has_configuration_evidence
                else "missing"
            ),
            "editable_geometry": (
                "F1_editable_K16_envelope_and_diameter_guides_not_F2_or_F3_geometry"
                if has_k16_envelope_flow_surrogate
                else "F1_editable_charge_air_envelopes_and_unpositioned_diameter_guides_not_F2_or_F3_geometry"
                if has_charge_air_chain_surrogate
                else "F1_editable_heat_shield_envelope_and_thermal_readiness_not_F2_or_F3_geometry"
                if has_heat_shield_thermal_surrogate
                else "F1_generated_nonspatial_turbo_lubrication_control_topology_not_part_geometry"
                if has_turbo_lubrication_control_topology
                else "F1_generated_nonspatial_oil_tank_circuit_topology_not_part_geometry"
                if has_oil_tank_circuit_topology
                else "F1_generated_nonspatial_oil_cooler_circuit_topology_not_part_geometry"
                if has_oil_cooler_circuit_topology
                else "F1_mass_constrained_structural_surrogate_and_virtual_F2_readiness_no_interface_geometry"
                if has_virtual_f2_readiness
                else "F1_editable_envelope_candidate_available_not_F2_interface_geometry"
                if catalogue_proxy_records
                else "F1_editable_valve_surrogate_available_not_analysis_or_F2_geometry"
                if has_valve_dimensional_surrogate
                else "missing"
            ),
            "measured_interfaces_and_tolerances": "missing",
            "selected_qualified_material": "missing",
            "loads_and_boundary_conditions": "missing",
            "reference_solver": "not_run",
            "physicsnemo": "not_run",
            "omniverse_simready": "not_run",
            "physical_correlation": "unavailable_by_program_constraint",
            "functional_manufacturing_release": False,
            "next_required_gate": next_gate,
        },
        "engineering_route": {
            "editable_cad_master_required": True,
            "engineering_archetype": archetype,
            "domain_routing_status": domain_routing_status,
            "classification_rule_id": classification_rule_id,
            "classification_confidence": classification_confidence,
            "classification_evidence_kind": (
                "description_keyword"
                if matched_description_terms
                else "primary_pet_system_context"
            ),
            "matched_description_terms": matched_description_terms,
            "human_reviewed_classification": False,
            "system_candidate_simulation_domain_ids": system_candidate_domains,
            "simulation_domain_ids": simulation_domains,
            "reference_solver_contracts": {
                domain_id: {
                    "reference_method": domain_contracts[domain_id]["reference_method"],
                    "required_geometry": domain_contracts[domain_id]["required_geometry"],
                }
                for domain_id in simulation_domains
            },
            "reference_solver_must_precede_physicsnemo": True,
            "physicsnemo_policy_ref": (
                "twins/vehicle-993/program-definition.json#/physicsnemo_policy"
            ),
            "physicsnemo_candidate_models": physicsnemo_candidates,
            "physicsnemo_selected_model": None,
            "physicsnemo_execution_enabled": physicsnemo_policy.get("execution_enabled"),
            "selected_material": None,
            "selected_manufacturing_route": None,
            "required_actions": required_actions,
        },
        "claims": {
            "human_reviewed_task": False,
            "dimensionally_accurate": False,
            "fitment_validated": False,
            "material_selected": False,
            "reference_simulation_passed": False,
            "physicsnemo_validated": False,
            "simready_validated": False,
            "manufacturing_released": False,
        },
    }


def build() -> tuple[dict[str, Any], dict[str, str]]:
    pet_index = load_json(PET_INDEX)
    roster = load_json(CONFIGURATION_ROSTER)
    part_links = load_json(CONFIGURATION_PART_LINKS)
    exceptions = load_json(CONFIGURATION_EXCEPTIONS)
    definition = load_json(PROGRAM_DEFINITION)
    manual_routing = load_json(MANUAL_EVIDENCE_ROUTING)
    catalog_crosswalk = load_json(CATALOG_CROSSWALK)
    engineering_evidence_links = load_json(ENGINEERING_EVIDENCE_LINKS)
    catalogue_twin_index = load_json(CATALOGUE_TWIN_INDEX)
    masters = load_part_masters(pet_index)
    routes = system_routes(definition)
    domain_contracts = simulation_domain_contracts(definition)
    physicsnemo_policy = definition["physicsnemo_policy"]
    manual_evidence_by_master = build_manual_evidence_map(manual_routing)
    catalog_engineering_by_master = build_catalog_engineering_map(catalog_crosswalk)
    simulation_evidence_by_master = build_simulation_evidence_map(
        engineering_evidence_links
    )
    catalogue_proxies_by_reference = build_catalogue_proxy_map(catalogue_twin_index)
    (
        configuration_ids_by_master,
        exception_ids_by_master,
        occurrence_ids_by_master,
        turbo_candidate_ids,
    ) = build_configuration_maps(roster, part_links, exceptions)
    master_ids = {str(master["twin_id"]) for master in masters}
    unknown_masters = (
        set(configuration_ids_by_master)
        | set(exception_ids_by_master)
        | set(occurrence_ids_by_master)
    ) - master_ids
    if unknown_masters:
        raise ContractError(f"configuration_evidence_unknown_masters:{sorted(unknown_masters)[:3]}")
    unknown_manual_masters = set(manual_evidence_by_master) - master_ids
    if unknown_manual_masters:
        raise ContractError(
            f"manual_evidence_unknown_masters:{sorted(unknown_manual_masters)[:3]}"
        )
    unknown_catalog_masters = set(catalog_engineering_by_master) - master_ids
    if unknown_catalog_masters:
        raise ContractError(
            f"catalog_engineering_unknown_masters:{sorted(unknown_catalog_masters)[:3]}"
        )
    unknown_simulation_evidence_masters = set(simulation_evidence_by_master) - master_ids
    if unknown_simulation_evidence_masters:
        raise ContractError(
            "simulation_evidence_unknown_masters:"
            f"{sorted(unknown_simulation_evidence_masters)[:3]}"
        )

    tasks = [
        build_task(
            master,
            routes=routes,
            configuration_ids=configuration_ids_by_master.get(str(master["twin_id"]), set()),
            exception_ids=exception_ids_by_master.get(str(master["twin_id"]), set()),
            constraint_occurrence_ids=occurrence_ids_by_master.get(
                str(master["twin_id"]), set()
            ),
            turbo_candidate_ids=turbo_candidate_ids,
            domain_contracts=domain_contracts,
            physicsnemo_policy=physicsnemo_policy,
            manual_evidence_candidates=manual_evidence_by_master.get(
                str(master["twin_id"]), []
            ),
            catalog_engineering_records=catalog_engineering_by_master.get(
                str(master["twin_id"]), []
            ),
            simulation_evidence_records=simulation_evidence_by_master.get(
                str(master["twin_id"]), []
            ),
            catalogue_proxy_records=catalogue_proxies_by_reference.get(
                str(master.get("subject", {}).get("normalized_oem_reference", "")),
                [],
            ),
        )
        for master in masters
    ]
    task_ids = [task["engineering_task_id"] for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise ContractError("engineering_task_id_collision")
    tasks.sort(key=lambda item: item["engineering_task_id"])

    shards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks:
        shard_id = sha256_text(task["subject"]["normalized_oem_reference"])[0]
        shards[shard_id].append(task)
    shard_texts: dict[str, str] = {}
    shard_index: list[dict[str, Any]] = []
    for shard_id in SHARD_IDS:
        records = sorted(shards[shard_id], key=lambda item: item["engineering_task_id"])
        content = "".join(canonical_json(record) + "\n" for record in records)
        shard_texts[shard_id] = content
        shard_index.append(
            {
                "shard_id": shard_id,
                "path": relative(DEFAULT_OUTPUT_ROOT / f"{shard_id}.jsonl"),
                "record_count": len(records),
                "sha256": sha256_text(content),
            }
        )

    priority_counts = Counter(task["risk_and_priority"]["priority"] for task in tasks)
    next_gate_counts = Counter(task["engineering_gates"]["next_required_gate"] for task in tasks)
    tier_counts = Counter(task["risk_and_priority"]["criticality_tier"] for task in tasks)
    archetype_counts = Counter(
        task["engineering_route"]["engineering_archetype"] for task in tasks
    )
    classification_rule_counts = Counter(
        task["engineering_route"]["classification_rule_id"] for task in tasks
    )
    classification_confidence_counts = Counter(
        task["engineering_route"]["classification_confidence"] for task in tasks
    )
    classification_evidence_counts = Counter(
        task["engineering_route"]["classification_evidence_kind"] for task in tasks
    )
    lexical_archetype_hypotheses = classification_evidence_counts[
        "description_keyword"
    ]
    system_fallback_archetype_hypotheses = classification_evidence_counts[
        "primary_pet_system_context"
    ]
    unclassified_archetype_routes = archetype_counts["system_level_unclassified"]
    tasks_with_configuration_evidence = sum(
        task["configuration_evidence"]["status"]
        == "candidate_or_exception_constraints_available"
        for task in tasks
    )
    tasks_with_candidate_links = sum(
        task["configuration_evidence"]["compatible_configuration_candidate_count"] > 0
        for task in tasks
    )
    tasks_with_exception_links = sum(
        bool(task["configuration_evidence"]["exception_contract_ids"]) for task in tasks
    )
    tasks_with_turbo_evidence = sum(
        task["configuration_evidence"]["turbo_integration_evidence"] for task in tasks
    )
    tasks_with_bbox = sum(task["input_evidence"]["declared_bounding_box_count"] > 0 for task in tasks)
    tasks_with_mass = sum(task["input_evidence"]["declared_mass_count"] > 0 for task in tasks)
    tasks_with_material_label = sum(
        task["input_evidence"]["non_placeholder_declared_material_count"] > 0 for task in tasks
    )
    tasks_with_manual_candidates = sum(
        task["workshop_manual_evidence"]["candidate_record_count"] > 0
        for task in tasks
    )
    manual_candidate_links = sum(
        task["workshop_manual_evidence"]["candidate_record_count"] for task in tasks
    )
    tasks_with_catalog_records = sum(
        task["catalog_part_engineering"]["record_count"] > 0 for task in tasks
    )
    catalog_record_links = sum(
        task["catalog_part_engineering"]["record_count"] for task in tasks
    )
    tasks_with_simulation_evidence = sum(
        task["linked_simulation_evidence"]["record_count"] > 0 for task in tasks
    )
    simulation_evidence_links = sum(
        task["linked_simulation_evidence"]["record_count"] for task in tasks
    )
    tasks_with_virtual_f2_readiness = sum(
        any(
            record.get("virtual_F2_readiness_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    virtual_f2_readiness_links = sum(
        sum(
            record.get("virtual_F2_readiness_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_mass_constrained_surrogate = sum(
        any(
            record.get("virtual_F2_readiness_contract", {}).get(
                "mass_constraint_closed"
            )
            is True
            for record in task["linked_simulation_evidence"]["records"]
            if record.get("virtual_F2_readiness_contract") is not None
        )
        for task in tasks
    )
    tasks_with_valve_dimensional_surrogate = sum(
        any(
            record.get("valve_dimensional_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    valve_dimensional_surrogate_links = sum(
        sum(
            record.get("valve_dimensional_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_k16_envelope_flow_surrogate = sum(
        any(
            record.get("k16_envelope_flow_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    k16_envelope_flow_surrogate_links = sum(
        sum(
            record.get("k16_envelope_flow_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_charge_air_chain_surrogate = sum(
        any(
            record.get("charge_air_chain_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    charge_air_chain_surrogate_links = sum(
        sum(
            record.get("charge_air_chain_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_heat_shield_thermal_surrogate = sum(
        any(
            record.get("heat_shield_thermal_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    heat_shield_thermal_surrogate_links = sum(
        sum(
            record.get("heat_shield_thermal_surrogate_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_turbo_lubrication_control_topology = sum(
        any(
            record.get("turbo_lubrication_control_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    turbo_lubrication_control_topology_links = sum(
        sum(
            record.get("turbo_lubrication_control_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_oil_tank_circuit_topology = sum(
        any(
            record.get("oil_tank_circuit_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    oil_tank_circuit_topology_links = sum(
        sum(
            record.get("oil_tank_circuit_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_oil_cooler_circuit_topology = sum(
        any(
            record.get("oil_cooler_circuit_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    oil_cooler_circuit_topology_links = sum(
        sum(
            record.get("oil_cooler_circuit_topology_contract") is not None
            for record in task["linked_simulation_evidence"]["records"]
        )
        for task in tasks
    )
    tasks_with_catalogue_proxy = sum(
        task["catalogue_proxy_geometry"]["record_count"] > 0 for task in tasks
    )
    catalogue_proxy_links = sum(
        task["catalogue_proxy_geometry"]["record_count"] for task in tasks
    )
    fidelity_counts = Counter(
        task["engineering_gates"]["current_fidelity"] for task in tasks
    )
    queue = sorted(
        tasks,
        key=lambda item: (
            item["risk_and_priority"]["priority_score"],
            0 if item["input_evidence"]["declared_bounding_box_count"] > 0 else 1,
            0 if item["input_evidence"]["declared_mass_count"] > 0 else 1,
            0
            if item["input_evidence"]["non_placeholder_declared_material_count"] > 0
            else 1,
            0 if item["catalog_part_engineering"]["record_count"] > 0 else 1,
            0
            if item["workshop_manual_evidence"]["candidate_record_count"] > 0
            else 1,
            item["engineering_task_id"],
        ),
    )
    first_batch = [
        {
            "engineering_task_id": task["engineering_task_id"],
            "part_master_twin_id": task["part_master_twin_id"],
            "normalized_oem_reference": task["subject"]["normalized_oem_reference"],
            "priority": task["risk_and_priority"]["priority"],
            "criticality_tier": task["risk_and_priority"]["criticality_tier"],
            "declared_bounding_box_available": (
                task["input_evidence"]["declared_bounding_box_count"] > 0
            ),
            "declared_mass_available": task["input_evidence"]["declared_mass_count"] > 0,
            "declared_material_label_available": (
                task["input_evidence"]["non_placeholder_declared_material_count"] > 0
            ),
            "linked_catalog_part_engineering_record_count": task[
                "catalog_part_engineering"
            ]["record_count"],
            "workshop_manual_candidate_record_count": task[
                "workshop_manual_evidence"
            ]["candidate_record_count"],
            "next_required_gate": task["engineering_gates"]["next_required_gate"],
            "catalogue_proxy_candidate_count": task["catalogue_proxy_geometry"][
                "record_count"
            ],
        }
        for task in queue[:100]
    ]
    index = {
        "$comment": (
            "Index F0 de 6 013 taches d'ingenierie inverse, une par jumeau maitre PET. "
            "Les taches ordonnent les acquisitions; elles ne constituent ni CAO, ni calcul, ni validation."
        ),
        "schema_version": "1.0.0",
        "generated_by": relative(Path(__file__).resolve()),
        "source_boundary": {
            "pet_twin_index": relative(PET_INDEX),
            "pet_twin_index_sha256": sha256_file(PET_INDEX),
            "source_master_shards_verified": True,
            "configuration_roster": relative(CONFIGURATION_ROSTER),
            "configuration_roster_sha256": sha256_file(CONFIGURATION_ROSTER),
            "configuration_part_links": relative(CONFIGURATION_PART_LINKS),
            "configuration_part_links_sha256": sha256_file(CONFIGURATION_PART_LINKS),
            "configuration_exceptions": relative(CONFIGURATION_EXCEPTIONS),
            "configuration_exceptions_sha256": sha256_file(CONFIGURATION_EXCEPTIONS),
            "program_definition": relative(PROGRAM_DEFINITION),
            "program_definition_sha256": sha256_file(PROGRAM_DEFINITION),
            "manual_evidence_routing": relative(MANUAL_EVIDENCE_ROUTING),
            "manual_evidence_routing_sha256": sha256_file(MANUAL_EVIDENCE_ROUTING),
            "catalog_crosswalk": relative(CATALOG_CROSSWALK),
            "catalog_crosswalk_sha256": sha256_file(CATALOG_CROSSWALK),
            "engineering_evidence_links": relative(ENGINEERING_EVIDENCE_LINKS),
            "engineering_evidence_links_sha256": sha256_file(
                ENGINEERING_EVIDENCE_LINKS
            ),
            "catalogue_twin_index": relative(CATALOGUE_TWIN_INDEX),
            "catalogue_twin_index_sha256": sha256_file(CATALOGUE_TWIN_INDEX),
            "raw_pet_pdf_copied": False,
            "pet_illustrations_copied": False,
        },
        "scope": {
            "generation": "993",
            "part_master_twins": len(masters),
            "engineering_tasks": len(tasks),
            "tasks_with_configuration_evidence": tasks_with_configuration_evidence,
            "tasks_without_configuration_evidence": len(tasks) - tasks_with_configuration_evidence,
            "tasks_with_configuration_candidate_links": tasks_with_candidate_links,
            "tasks_with_exception_contract_links": tasks_with_exception_links,
            "tasks_with_turbo_integration_evidence": tasks_with_turbo_evidence,
            "tasks_with_declared_bounding_box": tasks_with_bbox,
            "tasks_with_declared_mass": tasks_with_mass,
            "tasks_with_non_placeholder_declared_material_label": tasks_with_material_label,
            "tasks_with_workshop_manual_candidates": tasks_with_manual_candidates,
            "workshop_manual_candidate_links": manual_candidate_links,
            "promoted_workshop_manual_measurements_or_torques": 0,
            "tasks_with_linked_catalog_part_engineering_records": tasks_with_catalog_records,
            "linked_catalog_part_engineering_record_links": catalog_record_links,
            "promoted_catalog_material_process_geometry_or_validation_claims": 0,
            "tasks_with_linked_simulation_evidence": tasks_with_simulation_evidence,
            "linked_simulation_evidence_record_links": simulation_evidence_links,
            "tasks_with_virtual_F2_readiness_contract": tasks_with_virtual_f2_readiness,
            "virtual_F2_readiness_contract_links": virtual_f2_readiness_links,
            "tasks_with_mass_constrained_structural_surrogate": (
                tasks_with_mass_constrained_surrogate
            ),
            "mass_constrained_structural_surrogate_component_credits": 0,
            "tasks_with_valve_dimensional_surrogate": (
                tasks_with_valve_dimensional_surrogate
            ),
            "valve_dimensional_surrogate_links": valve_dimensional_surrogate_links,
            "valve_dimensional_surrogate_component_CAE_credits": 0,
            "tasks_with_k16_envelope_flow_surrogate": (
                tasks_with_k16_envelope_flow_surrogate
            ),
            "k16_envelope_flow_surrogate_links": k16_envelope_flow_surrogate_links,
            "k16_evaluated_zeroD_operating_points": 0,
            "k16_envelope_flow_surrogate_component_CAE_credits": 0,
            "tasks_with_charge_air_chain_surrogate": (
                tasks_with_charge_air_chain_surrogate
            ),
            "charge_air_chain_surrogate_links": charge_air_chain_surrogate_links,
            "charge_air_evaluated_zeroD_operating_points": 0,
            "charge_air_chain_surrogate_component_CAE_credits": 0,
            "tasks_with_heat_shield_thermal_surrogate": (
                tasks_with_heat_shield_thermal_surrogate
            ),
            "heat_shield_thermal_surrogate_links": (
                heat_shield_thermal_surrogate_links
            ),
            "heat_shield_evaluated_thermal_operating_points": 0,
            "heat_shield_thermal_surrogate_component_CAE_credits": 0,
            "tasks_with_turbo_lubrication_control_topology_contract": (
                tasks_with_turbo_lubrication_control_topology
            ),
            "turbo_lubrication_control_topology_links": (
                turbo_lubrication_control_topology_links
            ),
            "turbo_lubrication_control_symbolic_equations": 10,
            "turbo_lubrication_control_blocked_load_cases": 6,
            "turbo_lubrication_control_component_CAE_credits": 0,
            "tasks_with_oil_tank_circuit_topology_contract": (
                tasks_with_oil_tank_circuit_topology
            ),
            "oil_tank_circuit_topology_links": oil_tank_circuit_topology_links,
            "oil_tank_circuit_symbolic_equations": 11,
            "oil_tank_circuit_blocked_load_cases": 7,
            "oil_tank_circuit_component_CAE_credits": 0,
            "tasks_with_oil_cooler_circuit_topology_contract": (
                tasks_with_oil_cooler_circuit_topology
            ),
            "oil_cooler_circuit_topology_links": oil_cooler_circuit_topology_links,
            "oil_cooler_circuit_symbolic_equations": 14,
            "oil_cooler_circuit_blocked_load_cases": 8,
            "oil_cooler_circuit_component_CAE_credits": 0,
            "tasks_with_exact_oem_F1_envelope_candidates": tasks_with_catalogue_proxy,
            "exact_oem_F1_envelope_candidate_links": catalogue_proxy_links,
            "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results": 0,
            "tasks_with_lexical_archetype_hypothesis": lexical_archetype_hypotheses,
            "tasks_with_system_fallback_archetype_hypothesis": system_fallback_archetype_hypotheses,
            "unclassified_archetype_routes": unclassified_archetype_routes,
            "human_reviewed_archetype_classifications": 0,
            "human_reviewed_engineering_tasks": 0,
            "configured_vehicle_bom_entries": 0,
        },
        "coverage": {
            "tasks_by_priority": dict(sorted(priority_counts.items())),
            "tasks_by_next_required_gate": dict(sorted(next_gate_counts.items())),
            "tasks_by_criticality_tier": dict(sorted(tier_counts.items())),
            "tasks_by_engineering_archetype": dict(sorted(archetype_counts.items())),
            "tasks_by_classification_rule": dict(
                sorted(classification_rule_counts.items())
            ),
            "tasks_by_classification_confidence": dict(
                sorted(classification_confidence_counts.items())
            ),
            "tasks_by_classification_evidence_kind": dict(
                sorted(classification_evidence_counts.items())
            ),
            "tasks_by_current_fidelity": dict(sorted(fidelity_counts.items())),
        },
        "classification_audit": {
            "status": "complete_hypothesis_routing_not_human_reviewed",
            "part_master_routes": len(tasks),
            "archetype_count": len(archetype_counts),
            "classification_rule_count": len(classification_rule_counts),
            "description_keyword_routes": lexical_archetype_hypotheses,
            "primary_pet_system_fallback_routes": system_fallback_archetype_hypotheses,
            "unclassified_routes": unclassified_archetype_routes,
            "human_reviewed_routes": 0,
            "policy": {
                "description_keywords_are_hypotheses": True,
                "system_fallback_is_part_classification": False,
                "simulation_domain_route_is_solver_result": False,
                "manual_or_geometry_review_required": True,
            },
        },
        "engineering_readiness": {
            "editable_geometry": 0,
            "F1_envelope_identity_linked_unvalidated": fidelity_counts[
                "F1_envelope_identity_linked_unvalidated"
            ],
            "F1_mass_constrained_structural_surrogate": (
                tasks_with_mass_constrained_surrogate
            ),
            "F1_valve_dimensional_surrogate_unvalidated": (
                tasks_with_valve_dimensional_surrogate
            ),
            "F1_k16_envelope_diameter_guides_unvalidated": (
                tasks_with_k16_envelope_flow_surrogate
            ),
            "F1_charge_air_chain_guides_unvalidated": (
                tasks_with_charge_air_chain_surrogate
            ),
            "F1_heat_shield_envelope_thermal_readiness_unvalidated": (
                tasks_with_heat_shield_thermal_surrogate
            ),
            "F1_turbo_lubrication_control_topology_readiness_unvalidated": (
                fidelity_counts[
                    "F1_turbo_lubrication_control_topology_readiness_unvalidated"
                ]
            ),
            "F1_oil_tank_circuit_topology_readiness_unvalidated": (
                fidelity_counts[
                    "F1_oil_tank_circuit_topology_readiness_unvalidated"
                ]
            ),
            "F1_oil_cooler_circuit_topology_readiness_unvalidated": (
                fidelity_counts[
                    "F1_oil_cooler_circuit_topology_readiness_unvalidated"
                ]
            ),
            "F1_mass_constrained_structural_surrogate_virtual_F2_readiness": (
                tasks_with_virtual_f2_readiness
            ),
            "F2_interface_geometry": 0,
            "measured_interface_sets": 0,
            "qualified_material_decisions": 0,
            "reference_solver_results": 0,
            "physicsnemo_results": 0,
            "simready_assets": 0,
            "physical_correlations": 0,
            "functional_manufacturing_releases": 0,
            "functioning_vehicle_claim": False,
        },
        "shared_execution_policies": {
            "physicsnemo": {
                "policy_ref": "twins/vehicle-993/program-definition.json#/physicsnemo_policy",
                "role": physicsnemo_policy.get("role"),
                "discovered_commit": physicsnemo_policy.get("discovered_commit"),
                "verified_model_families": physicsnemo_policy.get(
                    "verified_model_families", []
                ),
                "execution_enabled": physicsnemo_policy.get("execution_enabled"),
            },
            "omniverse": {
                "policy_ref": "twins/vehicle-993/program-definition.json#/omniverse_policy",
                "property_assignment_intent": definition["omniverse_policy"].get(
                    "property_assignment_intent"
                ),
                "current_status": definition["omniverse_policy"].get("current_status"),
                "blockers": definition["omniverse_policy"].get("blockers", []),
                "required_stage_order": definition["omniverse_policy"].get(
                    "required_stage_order", []
                ),
                "simready_claim": definition["omniverse_policy"].get("simready_claim"),
            },
        },
        "first_engineering_batch": {
            "selection_status": (
                "generated_priority_queue_prefers_declared_geometry_mass_material_catalog_records_and_manual_candidates_not_human_reviewed"
            ),
            "batch_size": len(first_batch),
            "tasks": first_batch,
        },
        "output": {
            "format": "canonical_JSONL_one_record_per_part_master_engineering_task",
            "root": relative(DEFAULT_OUTPUT_ROOT),
            "shards": shard_index,
        },
        "prohibited_claims": [
            "engineering_task_is_editable_geometry",
            "declared_bounding_box_is_analysis_geometry",
            "source_material_label_is_selected_qualified_material",
            "configuration_constraint_is_complete_vehicle_bom",
            "priority_queue_is_engineering_validation",
            "task_generation_authorizes_manufacturing_or_road_use",
        ],
    }
    return index, shard_texts


def validate_index(index: dict[str, Any]) -> None:
    source_index = load_json(PET_INDEX)
    scope = index.get("scope", {})
    readiness = index.get("engineering_readiness", {})
    expected_tasks = source_index.get("scope", {}).get("part_master_twins")
    if scope.get("engineering_tasks") != expected_tasks or scope.get("part_master_twins") != expected_tasks:
        raise ContractError("engineering_task_count")
    if scope.get("tasks_with_configuration_evidence") + scope.get(
        "tasks_without_configuration_evidence"
    ) != expected_tasks:
        raise ContractError("configuration_evidence_partition")
    if scope.get("human_reviewed_engineering_tasks") != 0:
        raise ContractError("human_review_overclaim")
    if scope.get("configured_vehicle_bom_entries") != 0:
        raise ContractError("configured_bom_overclaim")
    if scope.get("tasks_with_lexical_archetype_hypothesis", 0) + scope.get(
        "tasks_with_system_fallback_archetype_hypothesis", 0
    ) != expected_tasks:
        raise ContractError("classification_evidence_partition")
    if scope.get("unclassified_archetype_routes") != 0:
        raise ContractError("unclassified_archetype_routes")
    if scope.get("human_reviewed_archetype_classifications") != 0:
        raise ContractError("classification_human_review_overclaim")
    if scope.get("promoted_workshop_manual_measurements_or_torques") != 0:
        raise ContractError("manual_evidence_promotion_overclaim")
    if scope.get("promoted_catalog_material_process_geometry_or_validation_claims") != 0:
        raise ContractError("catalog_engineering_promotion_overclaim")
    if scope.get(
        "promoted_linked_reference_solver_physicsnemo_simready_or_manufacturing_results"
    ) != 0:
        raise ContractError("linked_simulation_evidence_promotion_overclaim")
    manual_contract = load_json(MANUAL_EVIDENCE_ROUTING)
    manual_scope = manual_contract.get("scope", {})
    if scope.get("tasks_with_workshop_manual_candidates") != manual_scope.get(
        "part_master_twins_with_candidates"
    ):
        raise ContractError("manual_candidate_task_coverage")
    if scope.get("workshop_manual_candidate_links") != manual_scope.get(
        "part_review_candidate_links"
    ):
        raise ContractError("manual_candidate_link_coverage")
    boundary = index.get("source_boundary", {})
    if boundary.get("manual_evidence_routing_sha256") != sha256_file(
        MANUAL_EVIDENCE_ROUTING
    ):
        raise ContractError("manual_evidence_routing_digest")
    crosswalk = load_json(CATALOG_CROSSWALK)
    expected_catalog_masters = {
        match["part_master_twin_id"]
        for entry in crosswalk.get("parts", [])
        if isinstance(entry, dict)
        for match in entry.get("pet_occurrence_matches", [])
        if isinstance(match, dict) and isinstance(match.get("part_master_twin_id"), str)
    }
    if scope.get("tasks_with_linked_catalog_part_engineering_records") != len(
        expected_catalog_masters
    ):
        raise ContractError("catalog_engineering_task_coverage")
    if boundary.get("catalog_crosswalk_sha256") != sha256_file(CATALOG_CROSSWALK):
        raise ContractError("catalog_crosswalk_digest")
    simulation_evidence = load_json(ENGINEERING_EVIDENCE_LINKS)
    all_simulation_links = [
        link
        for key in ("links", "declared_reference_links")
        for link in simulation_evidence.get(key, [])
        if isinstance(link, dict)
    ]
    expected_simulation_masters = {
        master_id
        for link in all_simulation_links
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    expected_simulation_links = sum(
        len(link.get("pet_part_master_twin_ids", []))
        for link in all_simulation_links
    )
    if scope.get("tasks_with_linked_simulation_evidence") != len(
        expected_simulation_masters
    ):
        raise ContractError("simulation_evidence_task_coverage")
    if scope.get("linked_simulation_evidence_record_links") != expected_simulation_links:
        raise ContractError("simulation_evidence_link_coverage")
    expected_virtual_f2_links = sum(
        link.get("virtual_F2_readiness_contract") is not None
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_virtual_f2_masters = {
        master_id
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        and link.get("virtual_F2_readiness_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_virtual_F2_readiness_contract") != len(
        expected_virtual_f2_masters
    ):
        raise ContractError("virtual_F2_readiness_task_coverage")
    if scope.get("virtual_F2_readiness_contract_links") != expected_virtual_f2_links:
        raise ContractError("virtual_F2_readiness_link_coverage")
    if scope.get("tasks_with_mass_constrained_structural_surrogate") != 1:
        raise ContractError("mass_constrained_surrogate_task_coverage")
    if scope.get("mass_constrained_structural_surrogate_component_credits") != 0:
        raise ContractError("mass_constrained_surrogate_component_overclaim")
    expected_valve_surrogate_links = sum(
        link.get("valve_dimensional_surrogate_contract") is not None
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_valve_surrogate_masters = {
        master_id
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        and link.get("valve_dimensional_surrogate_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_valve_dimensional_surrogate") != len(
        expected_valve_surrogate_masters
    ):
        raise ContractError("valve_dimensional_surrogate_task_coverage")
    if scope.get("valve_dimensional_surrogate_links") != expected_valve_surrogate_links:
        raise ContractError("valve_dimensional_surrogate_link_coverage")
    if scope.get("valve_dimensional_surrogate_component_CAE_credits") != 0:
        raise ContractError("valve_dimensional_surrogate_component_overclaim")
    expected_k16_surrogate_links = sum(
        link.get("k16_envelope_flow_surrogate_contract") is not None
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_k16_surrogate_masters = {
        master_id
        for link in simulation_evidence.get("links", [])
        if isinstance(link, dict)
        and link.get("k16_envelope_flow_surrogate_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_k16_envelope_flow_surrogate") != len(
        expected_k16_surrogate_masters
    ):
        raise ContractError("k16_envelope_flow_surrogate_task_coverage")
    if scope.get("k16_envelope_flow_surrogate_links") != expected_k16_surrogate_links:
        raise ContractError("k16_envelope_flow_surrogate_link_coverage")
    if scope.get("k16_evaluated_zeroD_operating_points") != 0:
        raise ContractError("k16_zeroD_operating_point_overclaim")
    if scope.get("k16_envelope_flow_surrogate_component_CAE_credits") != 0:
        raise ContractError("k16_envelope_flow_surrogate_component_overclaim")
    expected_charge_air_links = sum(
        link.get("charge_air_chain_surrogate_contract") is not None
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_charge_air_masters = {
        master_id
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        and link.get("charge_air_chain_surrogate_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_charge_air_chain_surrogate") != len(
        expected_charge_air_masters
    ):
        raise ContractError("charge_air_chain_surrogate_task_coverage")
    if scope.get("charge_air_chain_surrogate_links") != expected_charge_air_links:
        raise ContractError("charge_air_chain_surrogate_link_coverage")
    if scope.get("charge_air_evaluated_zeroD_operating_points") != 0:
        raise ContractError("charge_air_zeroD_operating_point_overclaim")
    if scope.get("charge_air_chain_surrogate_component_CAE_credits") != 0:
        raise ContractError("charge_air_chain_surrogate_component_overclaim")
    expected_heat_shield_links = sum(
        link.get("heat_shield_thermal_surrogate_contract") is not None
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_heat_shield_masters = {
        master_id
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        and link.get("heat_shield_thermal_surrogate_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_heat_shield_thermal_surrogate") != len(
        expected_heat_shield_masters
    ):
        raise ContractError("heat_shield_thermal_surrogate_task_coverage")
    if scope.get("heat_shield_thermal_surrogate_links") != (
        expected_heat_shield_links
    ):
        raise ContractError("heat_shield_thermal_surrogate_link_coverage")
    if scope.get("heat_shield_evaluated_thermal_operating_points") != 0:
        raise ContractError("heat_shield_thermal_operating_point_overclaim")
    if scope.get("heat_shield_thermal_surrogate_component_CAE_credits") != 0:
        raise ContractError("heat_shield_thermal_surrogate_component_overclaim")
    expected_turbo_topology_links = sum(
        link.get("turbo_lubrication_control_topology_contract") is not None
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_turbo_topology_masters = {
        master_id
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        and link.get("turbo_lubrication_control_topology_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_turbo_lubrication_control_topology_contract") != len(
        expected_turbo_topology_masters
    ):
        raise ContractError("turbo_lubrication_control_topology_task_coverage")
    if scope.get("turbo_lubrication_control_topology_links") != (
        expected_turbo_topology_links
    ):
        raise ContractError("turbo_lubrication_control_topology_link_coverage")
    if scope.get("turbo_lubrication_control_symbolic_equations") != 10:
        raise ContractError("turbo_lubrication_control_equation_coverage")
    if scope.get("turbo_lubrication_control_blocked_load_cases") != 6:
        raise ContractError("turbo_lubrication_control_load_case_coverage")
    if scope.get("turbo_lubrication_control_component_CAE_credits") != 0:
        raise ContractError("turbo_lubrication_control_component_overclaim")
    expected_oil_tank_topology_links = sum(
        link.get("oil_tank_circuit_topology_contract") is not None
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_oil_tank_topology_masters = {
        master_id
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        and link.get("oil_tank_circuit_topology_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_oil_tank_circuit_topology_contract") != len(
        expected_oil_tank_topology_masters
    ):
        raise ContractError("oil_tank_circuit_topology_task_coverage")
    if scope.get("oil_tank_circuit_topology_links") != (
        expected_oil_tank_topology_links
    ):
        raise ContractError("oil_tank_circuit_topology_link_coverage")
    if scope.get("oil_tank_circuit_symbolic_equations") != 11:
        raise ContractError("oil_tank_circuit_equation_coverage")
    if scope.get("oil_tank_circuit_blocked_load_cases") != 7:
        raise ContractError("oil_tank_circuit_load_case_coverage")
    if scope.get("oil_tank_circuit_component_CAE_credits") != 0:
        raise ContractError("oil_tank_circuit_component_overclaim")
    expected_oil_cooler_topology_links = sum(
        link.get("oil_cooler_circuit_topology_contract") is not None
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        for _master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(_master_id, str)
    )
    expected_oil_cooler_topology_masters = {
        master_id
        for link in simulation_evidence.get("declared_reference_links", [])
        if isinstance(link, dict)
        and link.get("oil_cooler_circuit_topology_contract") is not None
        for master_id in link.get("pet_part_master_twin_ids", [])
        if isinstance(master_id, str)
    }
    if scope.get("tasks_with_oil_cooler_circuit_topology_contract") != len(
        expected_oil_cooler_topology_masters
    ):
        raise ContractError("oil_cooler_circuit_topology_task_coverage")
    if scope.get("oil_cooler_circuit_topology_links") != (
        expected_oil_cooler_topology_links
    ):
        raise ContractError("oil_cooler_circuit_topology_link_coverage")
    if scope.get("oil_cooler_circuit_symbolic_equations") != 14:
        raise ContractError("oil_cooler_circuit_equation_coverage")
    if scope.get("oil_cooler_circuit_blocked_load_cases") != 8:
        raise ContractError("oil_cooler_circuit_load_case_coverage")
    if scope.get("oil_cooler_circuit_component_CAE_credits") != 0:
        raise ContractError("oil_cooler_circuit_component_overclaim")
    if boundary.get("engineering_evidence_links_sha256") != sha256_file(
        ENGINEERING_EVIDENCE_LINKS
    ):
        raise ContractError("engineering_evidence_links_digest")
    catalogue_twin_index = load_json(CATALOGUE_TWIN_INDEX)
    proxy_map = build_catalogue_proxy_map(catalogue_twin_index)
    indexed_masters = load_part_masters(source_index)
    master_by_reference = {
        str(master.get("subject", {}).get("normalized_oem_reference", "")): str(
            master["twin_id"]
        )
        for master in indexed_masters
    }
    master_references = set(master_by_reference)
    expected_proxy_links = sum(
        len(records)
        for reference, records in proxy_map.items()
        if reference in master_references
    )
    expected_proxy_masters = {
        master_by_reference[reference]
        for reference, records in proxy_map.items()
        if reference in master_references and records
    }
    expected_proxy_tasks = len(expected_proxy_masters)
    if scope.get("tasks_with_exact_oem_F1_envelope_candidates") != expected_proxy_tasks:
        raise ContractError("catalogue_proxy_task_coverage")
    if scope.get("exact_oem_F1_envelope_candidate_links") != expected_proxy_links:
        raise ContractError("catalogue_proxy_link_coverage")
    if boundary.get("catalogue_twin_index_sha256") != sha256_file(
        CATALOGUE_TWIN_INDEX
    ):
        raise ContractError("catalogue_twin_index_digest")
    expected_current_envelope_tasks = len(
        expected_proxy_masters
        - expected_k16_surrogate_masters
        - expected_charge_air_masters
        - expected_heat_shield_masters
        - expected_turbo_topology_masters
        - expected_oil_tank_topology_masters
        - expected_oil_cooler_topology_masters
        - expected_virtual_f2_masters
    )
    if readiness.get("F1_envelope_identity_linked_unvalidated") != (
        expected_current_envelope_tasks
    ):
        raise ContractError("F1_envelope_readiness_coverage")
    if readiness.get("F1_mass_constrained_structural_surrogate") != 1:
        raise ContractError("F1_mass_constrained_surrogate_coverage")
    if readiness.get("F1_valve_dimensional_surrogate_unvalidated") != len(
        expected_valve_surrogate_masters
    ):
        raise ContractError("F1_valve_dimensional_surrogate_coverage")
    if readiness.get("F1_k16_envelope_diameter_guides_unvalidated") != len(
        expected_k16_surrogate_masters
    ):
        raise ContractError("F1_k16_envelope_flow_surrogate_coverage")
    if readiness.get("F1_charge_air_chain_guides_unvalidated") != len(
        expected_charge_air_masters
    ):
        raise ContractError("F1_charge_air_chain_surrogate_coverage")
    if readiness.get("F1_heat_shield_envelope_thermal_readiness_unvalidated") != len(
        expected_heat_shield_masters
    ):
        raise ContractError("F1_heat_shield_thermal_surrogate_coverage")
    expected_topology_fidelity_masters = (
        expected_turbo_topology_masters
        - expected_k16_surrogate_masters
        - expected_charge_air_masters
        - expected_heat_shield_masters
        - expected_virtual_f2_masters
    )
    if readiness.get(
        "F1_turbo_lubrication_control_topology_readiness_unvalidated"
    ) != len(expected_topology_fidelity_masters):
        raise ContractError("F1_turbo_lubrication_control_topology_coverage")
    expected_oil_tank_fidelity_masters = (
        expected_oil_tank_topology_masters
        - expected_k16_surrogate_masters
        - expected_charge_air_masters
        - expected_heat_shield_masters
        - expected_turbo_topology_masters
        - expected_virtual_f2_masters
    )
    if readiness.get(
        "F1_oil_tank_circuit_topology_readiness_unvalidated"
    ) != len(expected_oil_tank_fidelity_masters):
        raise ContractError("F1_oil_tank_circuit_topology_coverage")
    expected_oil_cooler_fidelity_masters = (
        expected_oil_cooler_topology_masters
        - expected_k16_surrogate_masters
        - expected_charge_air_masters
        - expected_heat_shield_masters
        - expected_turbo_topology_masters
        - expected_oil_tank_topology_masters
        - expected_virtual_f2_masters
    )
    if readiness.get(
        "F1_oil_cooler_circuit_topology_readiness_unvalidated"
    ) != len(expected_oil_cooler_fidelity_masters):
        raise ContractError("F1_oil_cooler_circuit_topology_coverage")
    if readiness.get(
        "F1_mass_constrained_structural_surrogate_virtual_F2_readiness"
    ) != len(expected_virtual_f2_masters):
        raise ContractError("F1_mass_constrained_virtual_F2_readiness_coverage")
    if readiness.get("F2_interface_geometry") != 0:
        raise ContractError("F2_interface_geometry_overclaim")
    for field in (
        "editable_geometry",
        "measured_interface_sets",
        "qualified_material_decisions",
        "reference_solver_results",
        "physicsnemo_results",
        "simready_assets",
        "physical_correlations",
        "functional_manufacturing_releases",
    ):
        if readiness.get(field) != 0:
            raise ContractError(f"readiness_overclaim:{field}")
    if readiness.get("functioning_vehicle_claim") is not False:
        raise ContractError("functioning_vehicle_overclaim")
    policies = index.get("shared_execution_policies", {})
    if policies.get("physicsnemo", {}).get("execution_enabled") is not False:
        raise ContractError("physicsnemo_execution_overclaim")
    if policies.get("omniverse", {}).get("current_status") != "blocked_before_preflight":
        raise ContractError("omniverse_status_overclaim")
    if policies.get("omniverse", {}).get("simready_claim") is not False:
        raise ContractError("omniverse_simready_overclaim")
    shards = index.get("output", {}).get("shards")
    if not isinstance(shards, list) or [item.get("shard_id") for item in shards] != list(SHARD_IDS):
        raise ContractError("engineering_shards")
    if sum(item.get("record_count", 0) for item in shards) != expected_tasks:
        raise ContractError("engineering_shard_count")
    if any(not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64 for item in shards):
        raise ContractError("engineering_shard_digest")
    coverage = index.get("coverage", {})
    if sum(coverage.get("tasks_by_priority", {}).values()) != expected_tasks:
        raise ContractError("priority_coverage")
    if sum(coverage.get("tasks_by_next_required_gate", {}).values()) != expected_tasks:
        raise ContractError("next_gate_coverage")
    if sum(coverage.get("tasks_by_criticality_tier", {}).values()) != expected_tasks:
        raise ContractError("criticality_coverage")
    if sum(coverage.get("tasks_by_engineering_archetype", {}).values()) != expected_tasks:
        raise ContractError("engineering_archetype_coverage")
    if sum(coverage.get("tasks_by_classification_rule", {}).values()) != expected_tasks:
        raise ContractError("classification_rule_coverage")
    if sum(
        coverage.get("tasks_by_classification_confidence", {}).values()
    ) != expected_tasks:
        raise ContractError("classification_confidence_coverage")
    if sum(
        coverage.get("tasks_by_classification_evidence_kind", {}).values()
    ) != expected_tasks:
        raise ContractError("classification_evidence_coverage")
    if sum(coverage.get("tasks_by_current_fidelity", {}).values()) != expected_tasks:
        raise ContractError("current_fidelity_coverage")
    audit = index.get("classification_audit", {})
    if audit.get("part_master_routes") != expected_tasks:
        raise ContractError("classification_audit_route_count")
    if audit.get("unclassified_routes") != 0:
        raise ContractError("classification_audit_unclassified")
    if audit.get("human_reviewed_routes") != 0:
        raise ContractError("classification_audit_human_review_overclaim")
    if audit.get("description_keyword_routes") + audit.get(
        "primary_pet_system_fallback_routes"
    ) != expected_tasks:
        raise ContractError("classification_audit_partition")
    policy = audit.get("policy", {})
    if policy.get("description_keywords_are_hypotheses") is not True:
        raise ContractError("classification_audit_lexical_boundary")
    if policy.get("system_fallback_is_part_classification") is not False:
        raise ContractError("classification_audit_system_fallback_boundary")
    first_batch = index.get("first_engineering_batch", {})
    tasks = first_batch.get("tasks")
    if not isinstance(tasks, list) or first_batch.get("batch_size") != len(tasks):
        raise ContractError("first_engineering_batch_count")
    if len(tasks) != min(100, expected_tasks):
        raise ContractError("first_engineering_batch_size")
    task_ids = [item.get("engineering_task_id") for item in tasks]
    if None in task_ids or len(task_ids) != len(set(task_ids)):
        raise ContractError("first_engineering_batch_ids")
    if boundary.get("source_master_shards_verified") is not True:
        raise ContractError("source_master_shards_not_verified")
    if boundary.get("raw_pet_pdf_copied") is not False:
        raise ContractError("raw_pet_pdf_boundary")
    if boundary.get("pet_illustrations_copied") is not False:
        raise ContractError("pet_illustration_boundary")


def write_outputs(index: dict[str, Any], shard_texts: dict[str, str], output_root: Path) -> None:
    if output_root.resolve() != DEFAULT_OUTPUT_ROOT.resolve():
        raise ContractError("custom_output_root_not_supported")
    output_root.mkdir(parents=True, exist_ok=True)
    for shard_id, content in shard_texts.items():
        (output_root / f"{shard_id}.jsonl").write_text(content, encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_json(index), encoding="utf-8")


def check_outputs(index: dict[str, Any], shard_texts: dict[str, str], output_root: Path) -> list[str]:
    errors: list[str] = []
    expected_index = render_json(index)
    if not OUTPUT.is_file():
        errors.append(f"missing:{OUTPUT}")
    elif OUTPUT.read_text(encoding="utf-8") != expected_index:
        errors.append(f"stale:{OUTPUT}")
    for shard_id, content in shard_texts.items():
        path = output_root / f"{shard_id}.jsonl"
        if not path.is_file():
            errors.append(f"missing:{path}")
        elif path.read_text(encoding="utf-8") != content:
            errors.append(f"stale:{path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--check-index", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    try:
        if args.check_index:
            validate_index(load_json(OUTPUT))
            print(f"valid {relative(OUTPUT)}")
            return 0
        index, shards = build()
        validate_index(index)
        if args.write:
            write_outputs(index, shards, args.output_root)
            print(
                f"wrote {index['scope']['engineering_tasks']} engineering tasks across "
                f"{len(shards)} shards and {relative(OUTPUT)}"
            )
            return 0
        errors = check_outputs(index, shards, args.output_root)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"current {relative(OUTPUT)} and {relative(args.output_root)}")
        return 0
    except ContractError as exc:
        print(f"PET 993 engineering readiness error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
