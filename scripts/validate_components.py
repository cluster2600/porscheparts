#!/usr/bin/env python3
"""Validate complete physical components and their sourced assemblies."""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ROOT / "catalog" / "components"
ASSEMBLIES = ROOT / "catalog" / "assemblies"
SOURCES = ROOT / "catalog" / "sources"
MEASUREMENTS = ROOT / "catalog" / "measurements"
TWINS = ROOT / "catalog" / "twins"
COMPONENT_ID = re.compile(r"^COMP-[A-Z0-9][A-Z0-9._-]{2,79}$")
ASSEMBLY_ID = re.compile(r"^ASM-[A-Z0-9][A-Z0-9._-]{2,79}$")
RELATION_ID = re.compile(r"^[A-Z0-9][A-Z0-9_]{2,79}$")
NAMED_INTERFACE = re.compile(r"^[a-z][a-z0-9_]{2,79}$")
THREAD = re.compile(r"^M[0-9]+(\.[0-9]+)?x[0-9]+(\.[0-9]+)?$")
# Ids with this prefix are registry ids: they must resolve to a record in
# catalog/sources/ with the same URL. Older inline ids (FUCHS-PRODUCT, ...) are
# record-local and are not looked up.
REGISTRY_PREFIX = "SRC-"
ASSEMBLY_KEYS = {
    "schema_version", "assembly_id", "name", "vehicle", "status", "instances",
    "physical_summary", "relationship_sources", "known_limits",
}
OPTIONAL_ASSEMBLY_KEYS = {"mounting_relations"}
RELATION_KEYS = {"relation_id", "instance_ids", "counterpart", "fastener", "tightening_torque", "source_ids", "limits"}
FASTENER_KEYS = {"description", "thread", "seat", "count_per_unit", "count_parameter_id", "source_id"}
TORQUE_KEYS = {"value", "unit", "source_id", "measurement_refs", "corroborated_by"}
# A torque can only be backed by a transcription that is not raw OCR.
ADMISSIBLE_EXTRACTION = {"structured_derived", "manually_checked"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _load_json_records(directory: Path) -> list[dict]:
    records: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Another validator reports unreadable records; here they simply do not resolve.
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


@lru_cache(maxsize=1)
def source_registry() -> dict[str, Any]:
    """Map each registered source id to its URL."""
    return {
        record["source_id"]: record.get("url")
        for record in _load_json_records(SOURCES)
        if _text(record.get("source_id"))
    }


@lru_cache(maxsize=1)
def measurement_values() -> dict[str, dict[str, dict]]:
    """Map each measurement record id to its values, by value id."""
    registry: dict[str, dict[str, dict]] = {}
    for record in _load_json_records(MEASUREMENTS):
        identifier = record.get("measurement_id")
        if not _text(identifier):
            continue
        values = record.get("declared_values") or []
        registry[identifier] = {
            value["value_id"]: value
            for value in values
            if isinstance(value, dict) and _text(value.get("value_id"))
        }
    return registry


@lru_cache(maxsize=1)
def twin_interfaces() -> dict[str, set[str]]:
    """Map each twin record id to the ids of its interfaces."""
    registry: dict[str, set[str]] = {}
    for record in _load_json_records(TWINS):
        identifier = record.get("twin_id")
        if not _text(identifier):
            continue
        interfaces = record.get("interfaces") or []
        registry[identifier] = {
            interface["interface_id"]
            for interface in interfaces
            if isinstance(interface, dict) and _text(interface.get("interface_id"))
        }
    return registry


def _registry_errors(label: str, source_id: Any, url: Any, registry: dict[str, Any]) -> list[str]:
    if not isinstance(source_id, str) or not source_id.startswith(REGISTRY_PREFIX):
        return []
    if source_id not in registry:
        return [f"{label}: {source_id} is not a record in catalog/sources"]
    if registry[source_id] != url:
        return [f"{label}: URL differs from the catalog/sources record {source_id}"]
    return []


def _thread_key(value: Any) -> str:
    """Normalize a thread designation: 'M 14x 1,5' and 'M14x1.5' compare equal."""
    return re.sub(r"\s+", "", str(value)).replace(",", ".").lower()


def _file(value: str, field: str, errors: list[str]) -> None:
    if not value:
        return
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        errors.append(f"{field}: path escapes repository")
        return
    if not candidate.is_file():
        errors.append(f"{field}: referenced file does not exist: {value}")


def validate_component(record: Any, *, sources: dict[str, Any] | None = None) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    registry = source_registry() if sources is None else sources
    errors: list[str] = []
    expected = {"schema_version", "component_id", "name", "kind", "vehicle", "identifiers", "physical", "geometry", "sources", "eligibility"}
    if expected - record.keys():
        errors.append(f"root: missing fields: {', '.join(sorted(expected - record.keys()))}")
    if record.keys() - expected:
        errors.append(f"root: unknown fields: {', '.join(sorted(record.keys() - expected))}")
    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = record.get("component_id")
    if not isinstance(identifier, str) or not COMPONENT_ID.fullmatch(identifier):
        errors.append("component_id: invalid")
    if not _text(record.get("name")):
        errors.append("name: expected a non-empty string")
    if record.get("kind") not in {"oem", "aftermarket", "standard", "measured_original"}:
        errors.append("kind: unknown")

    sources = record.get("sources")
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources: expected at least one source")
        sources = []
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{label}: expected an object")
            continue
        source_id = source.get("source_id")
        if not _text(source_id):
            errors.append(f"{label}.source_id: expected text")
        elif source_id in source_ids:
            errors.append(f"{label}.source_id: duplicate")
        else:
            source_ids.add(source_id)
        if not _url(source.get("url")):
            errors.append(f"{label}.url: expected http(s) URL")
        errors.extend(_registry_errors(f"{label}.source_id", source_id, source.get("url"), registry))
        if not _date(source.get("accessed_on")):
            errors.append(f"{label}.accessed_on: expected YYYY-MM-DD")
        if not _text(source.get("license")):
            errors.append(f"{label}.license: expected text")
        if not isinstance(source.get("supports"), list) or not source.get("supports"):
            errors.append(f"{label}.supports: expected claims")

    physical = record.get("physical")
    if not isinstance(physical, dict):
        errors.append("physical: expected an object")
        physical = {}
    sizes = physical.get("size_parameters")
    if not isinstance(sizes, list) or not sizes:
        errors.append("physical.size_parameters: expected at least one parameter")
        sizes = []
    for index, parameter in enumerate(sizes):
        if not isinstance(parameter, dict) or not isinstance(parameter.get("value"), (int, float)):
            errors.append(f"physical.size_parameters[{index}]: invalid")
        elif parameter.get("source_id") not in source_ids:
            errors.append(f"physical.size_parameters[{index}].source_id: unknown source")
    mass = physical.get("mass")
    if not isinstance(mass, dict) or not isinstance(mass.get("value_g"), (int, float)) or mass.get("value_g", 0) <= 0:
        errors.append("physical.mass.value_g: expected a positive number")
    elif mass.get("source_id") not in source_ids:
        errors.append("physical.mass.source_id: unknown source")
    material = physical.get("material")
    if not isinstance(material, dict) or not _text(material.get("family")) or not _text(material.get("process")):
        errors.append("physical.material: family and process are required")
    elif material.get("source_id") not in source_ids:
        errors.append("physical.material.source_id: unknown source")

    geometry = record.get("geometry")
    if not isinstance(geometry, dict):
        errors.append("geometry: expected an object")
        geometry = {}
    master_file = geometry.get("master_file")
    if not isinstance(master_file, str):
        errors.append("geometry.master_file: expected a string")
    else:
        _file(master_file, "geometry.master_file", errors)
    if geometry.get("representation") not in {"interface_proxy", "envelope", "detailed_solid", "scan"}:
        errors.append("geometry.representation: unknown")
    if not isinstance(geometry.get("limitations"), list) or not geometry.get("limitations"):
        errors.append("geometry.limitations: expected at least one limitation")

    eligibility = record.get("eligibility")
    if not isinstance(eligibility, dict):
        errors.append("eligibility: expected an object")
    elif eligibility.get("complete_physical_record") is True:
        if errors:
            errors.append("eligibility.complete_physical_record: cannot be true while the record is invalid")
        if eligibility.get("spatial_check") is True and geometry.get("interface_accuracy_mm") is None:
            errors.append("eligibility.spatial_check: requires known interface accuracy")
    return errors


def _validate_relations(
    relations: Any,
    instances: dict[str, dict],
    known_components: dict[str, dict],
    source_ids: set[str],
    measurements: dict[str, dict[str, dict]],
    twins: dict[str, set[str]],
) -> list[str]:
    """Check sourced fastening relations against the records they cite."""
    if not isinstance(relations, list):
        return ["mounting_relations: expected an array"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, relation in enumerate(relations):
        label = f"mounting_relations[{index}]"
        if not isinstance(relation, dict):
            errors.append(f"{label}: expected an object")
            continue
        if RELATION_KEYS - relation.keys():
            errors.append(f"{label}: missing fields: {', '.join(sorted(RELATION_KEYS - relation.keys()))}")
        if relation.keys() - RELATION_KEYS:
            errors.append(f"{label}: unknown fields: {', '.join(sorted(relation.keys() - RELATION_KEYS))}")
        relation_id = relation.get("relation_id")
        if not isinstance(relation_id, str) or not RELATION_ID.fullmatch(relation_id):
            errors.append(f"{label}.relation_id: invalid")
        elif relation_id in seen:
            errors.append(f"{label}.relation_id: duplicate")
        else:
            seen.add(relation_id)

        cited = relation.get("source_ids")
        if not isinstance(cited, list) or not cited:
            errors.append(f"{label}.source_ids: expected at least one source")
            cited = []
        for source_id in cited:
            if source_id not in source_ids:
                errors.append(f"{label}.source_ids: {source_id} is not a relationship source")

        def _cited(field: str, source_id: Any) -> None:
            if source_id not in cited:
                errors.append(f"{label}.{field}: {source_id} is not cited in source_ids")

        limits = relation.get("limits")
        if not isinstance(limits, list) or not limits or not all(_text(item) for item in limits):
            errors.append(f"{label}.limits: expected at least one limit")

        members = relation.get("instance_ids")
        components: list[dict] = []
        if not isinstance(members, list) or not members:
            errors.append(f"{label}.instance_ids: expected at least one instance")
            members = []
        for member in members:
            instance = instances.get(member)
            if instance is None:
                errors.append(f"{label}.instance_ids: unknown instance {member}")
            elif instance.get("component_id") in known_components:
                components.append(known_components[instance["component_id"]])

        counterpart = relation.get("counterpart")
        if not isinstance(counterpart, dict):
            errors.append(f"{label}.counterpart: expected an object")
        else:
            kind, ref = counterpart.get("kind"), counterpart.get("ref")
            if kind == "component":
                if ref not in known_components:
                    errors.append(f"{label}.counterpart.ref: unknown component")
            elif kind == "named_interface":
                if not isinstance(ref, str) or not NAMED_INTERFACE.fullmatch(ref):
                    errors.append(f"{label}.counterpart.ref: expected a lower_snake_case interface name")
            else:
                errors.append(f"{label}.counterpart.kind: expected component or named_interface")
            links = counterpart.get("twin_interfaces", [])
            if not isinstance(links, list):
                errors.append(f"{label}.counterpart.twin_interfaces: expected an array")
                links = []
            for link in links:
                if not isinstance(link, dict) or link.get("twin_id") not in twins:
                    errors.append(f"{label}.counterpart.twin_interfaces: unknown twin record")
                elif link.get("interface_id") not in twins[link["twin_id"]]:
                    errors.append(
                        f"{label}.counterpart.twin_interfaces: {link.get('interface_id')} is not an interface of {link['twin_id']}"
                    )

        fastener = relation.get("fastener")
        thread = None
        if not isinstance(fastener, dict):
            errors.append(f"{label}.fastener: expected an object")
        else:
            if fastener.keys() != FASTENER_KEYS:
                errors.append(f"{label}.fastener: expected exactly {', '.join(sorted(FASTENER_KEYS))}")
            if not _text(fastener.get("description")):
                errors.append(f"{label}.fastener.description: expected text")
            thread = fastener.get("thread")
            if thread is not None and (not isinstance(thread, str) or not THREAD.fullmatch(thread)):
                errors.append(f"{label}.fastener.thread: expected null or a designation such as M14x1.5")
            if fastener.get("seat") is not None and not _text(fastener.get("seat")):
                errors.append(f"{label}.fastener.seat: expected null or text")
            _cited("fastener.source_id", fastener.get("source_id"))
            count = fastener.get("count_per_unit")
            parameter_id = fastener.get("count_parameter_id")
            if count is None:
                if parameter_id is not None:
                    errors.append(f"{label}.fastener.count_parameter_id: must be null when the count is unknown")
            elif not isinstance(count, int) or isinstance(count, bool) or count < 1:
                errors.append(f"{label}.fastener.count_per_unit: expected null or a positive integer")
            elif not _text(parameter_id):
                errors.append(f"{label}.fastener.count_parameter_id: a count must name the component parameter that sources it")
            else:
                # The count is not typed here: it must equal a sourced count parameter of every member.
                for component in components:
                    parameters = component.get("physical", {}).get("size_parameters", [])
                    match = [item for item in parameters if isinstance(item, dict) and item.get("parameter_id") == parameter_id]
                    if not match or match[0].get("unit") != "count" or match[0].get("value") != count:
                        errors.append(
                            f"{label}.fastener.count_per_unit: {count} is not the {parameter_id} count of {component.get('component_id')}"
                        )

        torque = relation.get("tightening_torque")
        if torque is not None:
            if not isinstance(torque, dict):
                errors.append(f"{label}.tightening_torque: expected null or an object")
            else:
                if torque.keys() != TORQUE_KEYS:
                    errors.append(f"{label}.tightening_torque: expected exactly {', '.join(sorted(TORQUE_KEYS))}")
                value = torque.get("value")
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    errors.append(f"{label}.tightening_torque.value: expected a positive number")
                if torque.get("unit") != "Nm":
                    errors.append(f"{label}.tightening_torque.unit: expected Nm")
                _cited("tightening_torque.source_id", torque.get("source_id"))
                corroborated = torque.get("corroborated_by")
                if not isinstance(corroborated, list):
                    errors.append(f"{label}.tightening_torque.corroborated_by: expected an array")
                    corroborated = []
                for source_id in corroborated:
                    _cited("tightening_torque.corroborated_by", source_id)
                references = torque.get("measurement_refs")
                if not isinstance(references, list):
                    errors.append(f"{label}.tightening_torque.measurement_refs: expected an array")
                    references = []
                for position, reference in enumerate(references):
                    ref_label = f"{label}.tightening_torque.measurement_refs[{position}]"
                    if not isinstance(reference, dict):
                        errors.append(f"{ref_label}: expected an object")
                        continue
                    values = measurements.get(reference.get("measurement_id"))
                    if values is None:
                        errors.append(f"{ref_label}.measurement_id: unknown measurement record")
                        continue
                    entry = values.get(reference.get("value_id"))
                    if entry is None:
                        errors.append(f"{ref_label}.value_id: not in {reference.get('measurement_id')}")
                        continue
                    numbers = entry.get("numeric_values") or []
                    if entry.get("record_type") != "torque_spec":
                        errors.append(f"{ref_label}: the cited value is not a torque specification")
                    if entry.get("unit") != torque.get("unit") or not numbers or numbers[0] != value:
                        errors.append(f"{ref_label}: the cited value does not state {value} {torque.get('unit')}")
                    if entry.get("extraction_status") not in ADMISSIBLE_EXTRACTION:
                        errors.append(f"{ref_label}: extraction status {entry.get('extraction_status')} is not admissible")
                    if entry.get("source_id") != torque.get("source_id"):
                        errors.append(f"{ref_label}: the cited value belongs to another source")
                    stated = (entry.get("details") or {}).get("thread")
                    if thread is not None and stated and _thread_key(stated) != _thread_key(thread):
                        errors.append(f"{ref_label}: the cited value is for thread {stated}, not {thread}")
    return errors


def validate_assembly(
    record: Any,
    known_components: dict[str, dict],
    *,
    sources: dict[str, Any] | None = None,
    measurements: dict[str, dict[str, dict]] | None = None,
    twins: dict[str, set[str]] | None = None,
) -> list[str]:
    if not isinstance(record, dict):
        return ["root: expected an object"]
    registry = source_registry() if sources is None else sources
    measurement_registry = measurement_values() if measurements is None else measurements
    twin_registry = twin_interfaces() if twins is None else twins
    errors: list[str] = []
    if ASSEMBLY_KEYS - record.keys():
        errors.append(f"root: missing fields: {', '.join(sorted(ASSEMBLY_KEYS - record.keys()))}")
    if record.keys() - ASSEMBLY_KEYS - OPTIONAL_ASSEMBLY_KEYS:
        errors.append(f"root: unknown fields: {', '.join(sorted(record.keys() - ASSEMBLY_KEYS - OPTIONAL_ASSEMBLY_KEYS))}")
    if record.get("schema_version") != "1.0.0":
        errors.append("schema_version: expected 1.0.0")
    identifier = record.get("assembly_id")
    if not isinstance(identifier, str) or not ASSEMBLY_ID.fullmatch(identifier):
        errors.append("assembly_id: invalid")
    status = record.get("status")
    if status not in {"logical", "positioned", "interface_checked"}:
        errors.append("status: unknown")
    relationship_sources = record.get("relationship_sources")
    if not isinstance(relationship_sources, list):
        relationship_sources = []
    source_ids = {source.get("source_id") for source in relationship_sources if isinstance(source, dict)}
    if not relationship_sources:
        errors.append("relationship_sources: expected at least one source")
    for index, source in enumerate(relationship_sources):
        if isinstance(source, dict):
            errors.extend(
                _registry_errors(f"relationship_sources[{index}].source_id", source.get("source_id"), source.get("url"), registry)
            )
    instances = record.get("instances")
    calculated_mass = 0.0
    if not isinstance(instances, list) or len(instances) < 2:
        errors.append("instances: expected at least two instances")
        instances = []
    by_id: dict[str, dict] = {}
    for index, instance in enumerate(instances):
        label = f"instances[{index}]"
        if not isinstance(instance, dict):
            errors.append(f"{label}: expected an object")
            continue
        instance_id = instance.get("instance_id")
        if not _text(instance_id):
            errors.append(f"{label}.instance_id: expected text")
        elif instance_id in by_id:
            errors.append(f"{label}.instance_id: duplicate")
        else:
            by_id[instance_id] = instance
        component = known_components.get(instance.get("component_id"))
        if component is None:
            errors.append(f"{label}.component_id: unknown component")
        else:
            quantity = instance.get("quantity")
            if not isinstance(quantity, int) or quantity < 1:
                errors.append(f"{label}.quantity: expected a positive integer")
            else:
                calculated_mass += component["physical"]["mass"]["value_g"] * quantity
        if instance.get("relationship_source_id") not in source_ids:
            errors.append(f"{label}.relationship_source_id: unknown source")
        transform = instance.get("transform")
        if transform is not None and (not isinstance(transform, list) or len(transform) != 16):
            errors.append(f"{label}.transform: expected null or 16 values")
        if status in {"positioned", "interface_checked"} and transform is None:
            errors.append(f"{label}.transform: required for {status}")
    summary = record.get("physical_summary")
    if not isinstance(summary, dict) or not isinstance(summary.get("mass_g"), (int, float)):
        errors.append("physical_summary.mass_g: expected a number")
    elif abs(float(summary["mass_g"]) - calculated_mass) > 0.001:
        errors.append(
            f"physical_summary.mass_g: {summary['mass_g']} does not match component sum {calculated_mass}"
        )
    if isinstance(summary, dict) and summary.get("basis") != "sum_of_component_records":
        errors.append("physical_summary.basis: expected sum_of_component_records")
    if "mounting_relations" in record:
        errors.extend(
            _validate_relations(
                record["mounting_relations"], by_id, known_components, source_ids, measurement_registry, twin_registry
            )
        )
    return errors


def main() -> int:
    failed = False
    known: dict[str, dict] = {}
    component_files = sorted(COMPONENTS.glob("*.json"))
    if not component_files:
        print("components: no records found", file=sys.stderr)
        return 1
    for path in component_files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_component(record)
        except (OSError, json.JSONDecodeError) as exc:
            errors = [f"cannot load JSON: {exc}"]
            record = {}
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            known[record["component_id"]] = record
            print(f"valid {path.relative_to(ROOT)}")
    assembly_files = sorted(ASSEMBLIES.glob("*.json"))
    for path in assembly_files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_assembly(record, known)
        except (OSError, json.JSONDecodeError) as exc:
            errors = [f"cannot load JSON: {exc}"]
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            print(f"valid {path.relative_to(ROOT)}")
    print(f"components: {len(known)} valid, assemblies: {len(assembly_files)} checked")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
