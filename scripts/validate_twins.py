#!/usr/bin/env python3
"""Validate digital-twin zone records against the twin-record contract.

The contract is `catalog/schemas/twin.schema.json`. This script executes that
schema itself, with a small stdlib evaluator for the JSON Schema keywords the
schema uses, so the validator and the schema cannot drift apart: a keyword the
evaluator does not implement makes the schema load fail instead of being
skipped. On top of the schema it applies only the rules JSON Schema cannot
express — cross-field ordering, identifier uniqueness and references, the
generation token in the twin id, and case-exact file resolution. Both layers
are listed in `catalog/schemas/CHANGELOG.md`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "twins"
SCHEMA_PATH = ROOT / "catalog" / "schemas" / "twin.schema.json"
RETIRED_VERSIONS = {"1.0.0"}
TWIN_GENERATION = re.compile(r"^TWIN-([0-9]{3})-")

# Keywords the evaluator implements, and annotations it may ignore. Anything
# else in the schema is a contract change the validator would silently miss.
ASSERTIONS = {
    "type", "const", "enum", "pattern", "minLength", "minimum", "maximum",
    "exclusiveMinimum", "minItems", "maxItems", "uniqueItems", "items",
    "contains", "required", "properties", "additionalProperties", "allOf",
    "if", "then", "not", "$ref",
}
ANNOTATIONS = {"$schema", "$id", "title", "description", "$comment", "$defs"}


def _check_keywords(schema: Any, where: str = "#") -> None:
    if not isinstance(schema, dict):
        raise ValueError(f"{where}: a schema must be an object")
    unknown = schema.keys() - ASSERTIONS - ANNOTATIONS
    if unknown:
        raise ValueError(f"{where}: unsupported schema keywords {sorted(unknown)}")
    if "additionalProperties" in schema and not isinstance(schema["additionalProperties"], bool):
        raise ValueError(f"{where}: only boolean additionalProperties is supported")
    if "then" in schema and "if" not in schema:
        raise ValueError(f"{where}: then without if")
    for key in ("items", "contains", "not", "if", "then"):
        if key in schema:
            _check_keywords(schema[key], f"{where}/{key}")
    for key in ("properties", "$defs"):
        for name, sub in schema.get(key, {}).items():
            _check_keywords(sub, f"{where}/{key}/{name}")
    for index, sub in enumerate(schema.get("allOf", [])):
        _check_keywords(sub, f"{where}/allOf/{index}")


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    _check_keywords(schema)
    return schema


@lru_cache(maxsize=None)
def _pattern(source: str) -> re.Pattern[str]:
    # ECMA-262 "$" matches only at the end of the input; Python's also matches
    # before a final newline, so translate a trailing anchor to \Z.
    if source.endswith("$") and not source.endswith("\\$"):
        source = source[:-1] + r"\Z"
    return re.compile(source)


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    return type(left) is type(right) and left == right


def _is_type(value: Any, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, {"string": str, "array": list, "object": dict}[name])


def _label(path: tuple[Any, ...]) -> str:
    text = ""
    for part in path:
        text += f"[{part}]" if isinstance(part, int) else (f".{part}" if text else str(part))
    return text or "root"


def _evaluate(value: Any, schema: dict[str, Any], path: tuple[Any, ...], errors: list[str]) -> None:
    here = _label(path)
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/$defs/"):
            raise ValueError(f"unsupported $ref {reference}")
        _evaluate(value, load_schema()["$defs"][reference[len("#/$defs/"):]], path, errors)
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, name) for name in types):
            errors.append(f"{here}: expected {' or '.join(types)}")
            return
    if "const" in schema and not _equal(value, schema["const"]):
        errors.append(f"{here}: expected {json.dumps(schema['const'])}")
    if "enum" in schema and not any(_equal(value, item) for item in schema["enum"]):
        errors.append(f"{here}: expected one of {sorted(map(str, schema['enum']))}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{here}: expected at least {schema['minLength']} characters")
        if "pattern" in schema and not _pattern(schema["pattern"]).search(value):
            errors.append(f"{here}: does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{here}: expected at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{here}: expected at most {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{here}: expected more than {schema['exclusiveMinimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{here}: expected at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{here}: expected at most {schema['maxItems']} items")
        if schema.get("uniqueItems") and any(
            _equal(value[i], value[j]) for i in range(len(value)) for j in range(i + 1, len(value))
        ):
            errors.append(f"{here}: items must be unique")
        if "items" in schema:
            for index, item in enumerate(value):
                _evaluate(item, schema["items"], (*path, index), errors)
        if "contains" in schema and not any(_valid(item, schema["contains"]) for item in value):
            errors.append(f"{here}: no item matches the required item schema")
    if isinstance(value, dict):
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing:
            errors.append(f"{here}: missing fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        for key, sub in properties.items():
            if key in value:
                _evaluate(value[key], sub, (*path, key), errors)
        if schema.get("additionalProperties") is False:
            extra = sorted(value.keys() - properties.keys())
            if extra:
                errors.append(f"{here}: unknown fields: {', '.join(extra)}")
    for sub in schema.get("allOf", []):
        _evaluate(value, sub, path, errors)
    if "if" in schema and "then" in schema and _valid(value, schema["if"]):
        failures: list[str] = []
        _evaluate(value, schema["then"], path, failures)
        rule = schema.get("$comment")
        errors.extend(f"{failure} [rule: {rule}]" if rule else failure for failure in failures)
    if "not" in schema and _valid(value, schema["not"]):
        excluded = schema["not"]
        shown = json.dumps(excluded["const"]) if excluded.keys() == {"const"} else "the excluded schema"
        errors.append(f"{here}: must not be {shown}")


def _valid(value: Any, schema: dict[str, Any]) -> bool:
    errors: list[str] = []
    _evaluate(value, schema, (), errors)
    return not errors


def schema_errors(record: Any) -> list[str]:
    """Return the errors of `record` against the twin-record JSON Schema."""
    errors: list[str] = []
    _evaluate(record, load_schema(), (), errors)
    return errors


def _resolve(value: str) -> bool:
    """True when `value` names an existing repository file, letter case included."""
    candidate = ROOT.joinpath(*value.split("/"))
    if not candidate.is_file():
        return False
    current = ROOT
    for part in Path(value).parts:
        if part not in os.listdir(current):
            return False
        current = current / part
    return True


def _file(value: Any, field: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value:
        return
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT)
    except ValueError:
        errors.append(f"{field}: path escapes the repository: {value}")
        return
    if Path(value).is_absolute() or not _resolve(value):
        errors.append(f"{field}: referenced file does not exist: {value}")


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def semantic_errors(record: Any) -> list[str]:
    """Rules of the contract that JSON Schema cannot express."""
    if not isinstance(record, dict):
        return []
    errors: list[str] = []
    vehicle = _dict(record.get("vehicle"))
    years = _dict(vehicle.get("model_years"))
    start, end = years.get("from"), years.get("to")
    if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in (start, end)) and start > end:
        errors.append("vehicle.model_years: from must be <= to")
    twin_id = record.get("twin_id")
    token = TWIN_GENERATION.match(twin_id) if isinstance(twin_id, str) else None
    if token and token.group(1) != vehicle.get("generation"):
        errors.append(f"twin_id: names generation {token.group(1)} but vehicle.generation is {vehicle.get('generation')}")

    known: set[str] = set()
    for index, component in enumerate(_list(record.get("components"))):
        component = _dict(component)
        identifier = component.get("component_id")
        if isinstance(identifier, str):
            if identifier in known:
                errors.append(f"components[{index}].component_id: duplicate {identifier}")
            known.add(identifier)
        _file(component.get("geometry_file"), f"components[{index}].geometry_file", errors)

    seen: set[str] = set()
    for index, interface in enumerate(_list(record.get("interfaces"))):
        interface = _dict(interface)
        identifier = interface.get("interface_id")
        if isinstance(identifier, str):
            if identifier in seen:
                errors.append(f"interfaces[{index}].interface_id: duplicate {identifier}")
            seen.add(identifier)
        unknown = [ref for ref in _list(interface.get("components")) if ref not in known]
        if unknown:
            errors.append(f"interfaces[{index}].components: references an unknown component: {unknown}")

    geometry = _dict(record.get("geometry"))
    _file(geometry.get("master_file"), "geometry.master_file", errors)
    for index, item in enumerate(_list(geometry.get("derived_files"))):
        _file(item, f"geometry.derived_files[{index}]", errors)
    for index, item in enumerate(_list(_dict(record.get("validation")).get("evidence"))):
        _file(item, f"validation.evidence[{index}]", errors)
    return errors


def validate_twin(record: Any) -> list[str]:
    errors = schema_errors(record)
    if isinstance(record, dict) and record.get("schema_version") in RETIRED_VERSIONS:
        errors = [error for error in errors if not error.startswith("schema_version:")]
        errors.append(
            f"schema_version: {record['schema_version']} is retired; migrate the record to "
            f"{load_schema()['properties']['schema_version']['const']} (catalog/schemas/CHANGELOG.md)"
        )
    return errors + semantic_errors(record)


def load_and_validate(path: Path) -> list[str]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load JSON: {exc}"]
    return validate_twin(record)


def main() -> int:
    files = sorted(REGISTRY.glob("*.json"))
    if not files:
        print("No twin records found", file=sys.stderr)
        return 1
    failed = False
    for path in files:
        errors = load_and_validate(path)
        if errors:
            failed = True
            for error in errors:
                print(f"{path.relative_to(ROOT)}: {error}", file=sys.stderr)
        else:
            print(f"valid {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
