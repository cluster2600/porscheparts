#!/usr/bin/env python3
"""Validate the 993 operational-twin contract documents and their synthetic fixtures.

The documents are a slice contract, a model card, a parameter set, a calibration
register and an observation set (catalog/schemas/operational-twin.schema.json).
This script has no dependencies: it implements exactly the JSON Schema keywords
that schema uses, refuses any other keyword, and then applies the rules a schema
cannot express: hash bindings between documents, unit and frame conventions,
timebase requirements, calibration references and the privacy boundary.

    python3 scripts/validate_operational_twin.py            # committed bundle and fixtures
    python3 scripts/validate_operational_twin.py --json     # machine-readable result

Every error is reported as "CODE: message" so that negative fixtures and tests
can name the rule they break. Passing this validator checks structure and
bindings only; it never establishes physical correlation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "catalog" / "schemas"
SCHEMA_PATH = SCHEMA_DIR / "operational-twin.schema.json"
TWIN_DIR = ROOT / "twins" / "993-turbo-cooling-fan-operational-f0"
BUNDLE = {
    "slice_contract": TWIN_DIR / "contract" / "slice.json",
    "model_card": TWIN_DIR / "contract" / "model-card.json",
    "parameter_set": TWIN_DIR / "contract" / "parameters-synthetic-0001.json",
    "calibration_register": TWIN_DIR / "fixtures" / "calibration-register-synthetic-0001.json",
    "observation_set": TWIN_DIR / "fixtures" / "observations-synthetic-0001.json",
}
INVALID_FIXTURES = TWIN_DIR / "fixtures" / "invalid"

# Physical conversion factors the contract must reproduce exactly. A contract
# that edits one of them is wrong, not a new convention.
KNOWN_CONVERSIONS = {
    ("rad/s", "rad/s"): (1.0, 0.0),
    ("rpm", "rad/s"): (math.pi / 30.0, 0.0),
    ("K", "K"): (1.0, 0.0),
    ("degC", "K"): (1.0, 273.15),
    ("Pa", "Pa"): (1.0, 0.0),
    ("hPa", "Pa"): (100.0, 0.0),
    ("kPa", "Pa"): (1000.0, 0.0),
}

# Privacy boundary: keys that must never appear in any document, and a VIN-shaped
# token (17 characters, no I/O/Q, mixing letters and digits).
FORBIDDEN_KEYS = {
    "vin", "chassis_number", "chassis_no", "engine_number", "engine_serial", "gearbox_number",
    "serial_number", "registration", "registration_plate", "licence_plate", "license_plate",
    "plate", "owner", "owner_name", "email", "phone", "address", "gps", "latitude", "longitude",
}
VIN = re.compile(r"(?<![A-Za-z0-9])(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])(?=[A-HJ-NPR-Z0-9]*[0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9])")


# --------------------------------------------------------------------------- hashing

def canonical_bytes(document: Any) -> bytes:
    """Canonical JSON: sorted keys, no insignificant whitespace, UTF-8, non-ASCII kept."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def canonical_sha256(document: Any) -> str:
    return hashlib.sha256(canonical_bytes(document)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- schema subset

class SchemaError(Exception):
    """The schema itself uses a keyword this validator does not implement."""


ANNOTATIONS = {"$schema", "$id", "$comment", "$defs", "title", "description", "examples", "default"}
IMPLEMENTED = {
    "$ref", "type", "enum", "const", "pattern", "minLength", "maxLength", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "required", "properties", "additionalProperties",
    "propertyNames", "items", "prefixItems", "minItems", "maxItems", "uniqueItems", "oneOf",
    "anyOf", "allOf", "not", "if", "then", "else",
}


def _is_type(value: Any, name: str) -> bool:
    if name == "null":
        return value is None
    if name == "boolean":
        return isinstance(value, bool)
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if name == "string":
        return isinstance(value, str)
    if name == "array":
        return isinstance(value, list)
    if name == "object":
        return isinstance(value, dict)
    raise SchemaError(f"unknown type {name!r}")


class SchemaValidator:
    def __init__(self, root_schema: dict, schema_dir: Path = SCHEMA_DIR) -> None:
        self.root = root_schema
        self.schema_dir = schema_dir
        self._files: dict[str, dict] = {}

    def _resolve(self, ref: str, base: dict) -> tuple[dict, dict]:
        file_part, _, pointer = ref.partition("#")
        document = base
        if file_part:
            if "/" in file_part or not file_part.endswith(".schema.json"):
                raise SchemaError(f"only sibling schema files may be referenced: {ref}")
            if file_part not in self._files:
                self._files[file_part] = load_json(self.schema_dir / file_part)
            document = self._files[file_part]
        node: Any = document
        for token in [t for t in pointer.split("/") if t]:
            node = node[token.replace("~1", "/").replace("~0", "~")]
        return node, document

    def errors(self, instance: Any, schema: Any = None, path: str = "", base: dict | None = None) -> list[str]:
        base = self.root if base is None else base
        schema = base if schema is None else schema
        if schema is True:
            return []
        if schema is False:
            return [f"SCHEMA: {path or '/'}: no value is allowed here"]
        unknown = set(schema) - IMPLEMENTED - ANNOTATIONS - {k for k in schema if k.startswith("x-")}
        if unknown:
            raise SchemaError(f"unsupported schema keywords {sorted(unknown)} at {path or '/'}")
        where = path or "/"
        out: list[str] = []
        if "$ref" in schema:
            target, target_base = self._resolve(schema["$ref"], base)
            out += self.errors(instance, target, path, target_base)
        if "type" in schema:
            names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(instance, n) for n in names):
                return out + [f"SCHEMA: {where}: expected type {'|'.join(names)}"]
        if "const" in schema and not _same(instance, schema["const"]):
            out.append(f"SCHEMA: {where}: expected constant {schema['const']!r}")
        if "enum" in schema and not any(_same(instance, v) for v in schema["enum"]):
            out.append(f"SCHEMA: {where}: {instance!r} is not one of {schema['enum']}")
        if isinstance(instance, str):
            if "pattern" in schema and not re.search(schema["pattern"], instance):
                out.append(f"SCHEMA: {where}: {instance!r} does not match {schema['pattern']}")
            if len(instance) < schema.get("minLength", 0):
                out.append(f"SCHEMA: {where}: string shorter than {schema['minLength']}")
            if "maxLength" in schema and len(instance) > schema["maxLength"]:
                out.append(f"SCHEMA: {where}: string longer than {schema['maxLength']}")
        if _is_type(instance, "number"):
            if "minimum" in schema and instance < schema["minimum"]:
                out.append(f"SCHEMA: {where}: {instance} < minimum {schema['minimum']}")
            if "maximum" in schema and instance > schema["maximum"]:
                out.append(f"SCHEMA: {where}: {instance} > maximum {schema['maximum']}")
            if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
                out.append(f"SCHEMA: {where}: {instance} <= exclusive minimum {schema['exclusiveMinimum']}")
            if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
                out.append(f"SCHEMA: {where}: {instance} >= exclusive maximum {schema['exclusiveMaximum']}")
        if isinstance(instance, dict):
            for key in schema.get("required", []):
                if key not in instance:
                    out.append(f"SCHEMA: {where}: missing required field {key!r}")
            properties = schema.get("properties", {})
            for key, value in instance.items():
                child = f"{path}/{key}"
                if "propertyNames" in schema:
                    out += self.errors(key, schema["propertyNames"], child + "#name", base)
                if key in properties:
                    out += self.errors(value, properties[key], child, base)
                elif "additionalProperties" in schema:
                    if schema["additionalProperties"] is False:
                        out.append(f"SCHEMA: {where}: unknown field {key!r}")
                    else:
                        out += self.errors(value, schema["additionalProperties"], child, base)
        if isinstance(instance, list):
            if len(instance) < schema.get("minItems", 0):
                out.append(f"SCHEMA: {where}: fewer than {schema['minItems']} items")
            if "maxItems" in schema and len(instance) > schema["maxItems"]:
                out.append(f"SCHEMA: {where}: more than {schema['maxItems']} items")
            if schema.get("uniqueItems"):
                seen = [canonical_bytes(v) for v in instance]
                if len(seen) != len(set(seen)):
                    out.append(f"SCHEMA: {where}: items are not unique")
            prefix = schema.get("prefixItems", [])
            for index, value in enumerate(instance):
                if index < len(prefix):
                    out += self.errors(value, prefix[index], f"{path}/{index}", base)
                elif "items" in schema:
                    out += self.errors(value, schema["items"], f"{path}/{index}", base)
        for sub in schema.get("allOf", []):
            out += self.errors(instance, sub, path, base)
        if "anyOf" in schema and not any(not self.errors(instance, s, path, base) for s in schema["anyOf"]):
            out.append(f"SCHEMA: {where}: matches none of anyOf")
        if "oneOf" in schema:
            matches = [s for s in schema["oneOf"] if not self.errors(instance, s, path, base)]
            if len(matches) != 1:
                out.append(f"SCHEMA: {where}: matches {len(matches)} branches of oneOf, expected exactly 1")
        if "not" in schema and not self.errors(instance, schema["not"], path, base):
            out.append(f"SCHEMA: {where}: matches a forbidden form")
        if "if" in schema:
            branch = "then" if not self.errors(instance, schema["if"], path, base) else "else"
            if branch in schema:
                out += self.errors(instance, schema[branch], path, base)
        return out

    def validate_kind(self, document: Any) -> list[str]:
        if not isinstance(document, dict) or document.get("document_kind") not in self.root["$defs"]:
            return ["SCHEMA: /document_kind: unknown or missing document kind"]
        kind = document["document_kind"]
        if kind not in {"slice_contract", "model_card", "parameter_set", "calibration_register", "observation_set"}:
            return ["SCHEMA: /document_kind: not a top-level document kind"]
        return self.errors(document, self.root["$defs"][kind])


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return canonical_bytes(a) == canonical_bytes(b)


# --------------------------------------------------------------------------- shared conventions

def conversion(slice_contract: dict, unit: str) -> tuple[str, float, float] | None:
    """(canonical unit, scale, offset) for one accepted channel unit, from the contract table."""
    for row in slice_contract["unit_conversions"]:
        if row["from"] == unit:
            return row["to"], row["scale"], row["offset"]
    return None


def mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def rotation_errors(m: list[list[float]], tolerance: float = 1e-9) -> list[str]:
    errors = []
    for i in range(3):
        for j in range(3):
            dot = sum(m[k][i] * m[k][j] for k in range(3))
            if abs(dot - (1.0 if i == j else 0.0)) > tolerance:
                errors.append("columns are not orthonormal")
                break
        if errors:
            break
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    if abs(det - 1.0) > tolerance:
        errors.append(f"determinant {det:.6g} is not +1")
    return errors


def mount_in_parent(mount: dict) -> dict:
    """Sensor position and sensing axis expressed in the parent component frame."""
    rotation = mount["rotation_parent_from_sensor"]
    position = [a + b for a, b in zip(mat_vec(rotation, mount["position_sensor_mm"]), mount["translation_mm"])]
    result = {"position_mm": position}
    if "sensing_axis_sensor" in mount:
        axis = mount["sensing_axis_sensor"]
        norm = math.sqrt(sum(a * a for a in axis))
        result["axis"] = [a / norm for a in mat_vec(rotation, axis)] if norm > 0 else None
    return result


def station_errors(station: dict, placed: dict) -> list[str]:
    if station["kind"] == "axial_cylinder":
        x, y, z = placed["position_mm"]
        lo, hi = station["z_range_mm"]
        radius = math.hypot(x, y)
        if not lo <= z <= hi or radius > station["r_max_mm"]:
            return [f"position ({x:.6g}, {y:.6g}, {z:.6g}) mm lies outside station {station['station_id']}"]
        return []
    axis = placed.get("axis")
    if axis is None:
        return [f"station {station['station_id']} needs a non-zero sensing_axis_sensor"]
    if abs(axis[2]) < station["min_abs_axis_cosine"]:
        return [f"sensing axis cosine {axis[2]:.6g} with +Z is below {station['min_abs_axis_cosine']}"]
    return []


def walk(document: Any, path: str = ""):
    yield path, document
    if isinstance(document, dict):
        for key, value in document.items():
            yield from walk(value, f"{path}/{key}")
    elif isinstance(document, list):
        for index, value in enumerate(document):
            yield from walk(value, f"{path}/{index}")


def privacy_errors(document: Any, name: str) -> list[str]:
    errors = []
    for path, value in walk(document):
        if isinstance(value, dict):
            for key in value:
                if key.lower() in FORBIDDEN_KEYS:
                    errors.append(f"PRIVACY_FORBIDDEN_KEY: {name}{path}/{key}: identifying field is not allowed")
        elif isinstance(value, str) and VIN.search(value):
            errors.append(f"PRIVACY_VEHICLE_IDENTIFIER: {name}{path}: VIN-shaped token is not allowed")
    return errors


# --------------------------------------------------------------------------- semantic rules

def _ranges_ok(pair: list[float]) -> bool:
    return pair[0] < pair[1]


def check_slice(slice_contract: dict) -> list[str]:
    errors = []
    frames = {f["frame_id"] for f in slice_contract["frames"]}
    stations = {s["station_id"]: s for s in slice_contract["stations"]}
    quantities = {q["quantity_id"]: q for q in slice_contract["quantities"]}
    channels = {c["channel_id"]: c for c in slice_contract["channels"]}
    for station in stations.values():
        if station["frame_id"] not in frames:
            errors.append(f"FRAME_UNKNOWN: station {station['station_id']} uses undeclared frame {station['frame_id']}")
        if "z_range_mm" in station and not _ranges_ok(station["z_range_mm"]):
            errors.append(f"RANGE_INVALID: station {station['station_id']} z_range_mm is not increasing")
    table = {}
    for row in slice_contract["unit_conversions"]:
        key = (row["from"], row["to"])
        if row["from"] in {r[0] for r in table}:
            errors.append(f"UNIT_CONVERSION: unit {row['from']} has more than one conversion")
        table[key] = (row["scale"], row["offset"])
        known = KNOWN_CONVERSIONS.get(key)
        if known is None:
            errors.append(f"UNIT_CONVERSION: {row['from']} -> {row['to']} is not a known physical conversion")
        elif abs(known[0] - row["scale"]) > 1e-15 * known[0] or abs(known[1] - row["offset"]) > 1e-12:
            errors.append(f"UNIT_CONVERSION: {row['from']} -> {row['to']} must use scale {known[0]!r} and offset {known[1]!r}")
    for quantity in quantities.values():
        for unit in quantity["accepted_units"]:
            if (unit, quantity["canonical_unit"]) not in table:
                errors.append(f"UNIT_CONVERSION: {quantity['quantity_id']} accepts {unit} without a conversion to {quantity['canonical_unit']}")
    for channel in channels.values():
        if channel["quantity_id"] not in quantities:
            errors.append(f"QUANTITY_UNKNOWN: channel {channel['channel_id']} uses {channel['quantity_id']}")
        if channel["station_id"] is not None and channel["station_id"] not in stations:
            errors.append(f"STATION_UNKNOWN: channel {channel['channel_id']} uses {channel['station_id']}")
        if channel["max_age_s"] < channel["nominal_period_s"]:
            errors.append(f"CADENCE: channel {channel['channel_id']} max_age_s is shorter than its nominal period")
        if not _ranges_ok(channel["plausible_range_canonical"]):
            errors.append(f"RANGE_INVALID: channel {channel['channel_id']} plausible range is not increasing")
    prediction = slice_contract["prediction"]
    for name in prediction["inputs"]:
        if channels.get(name, {}).get("role") != "input":
            errors.append(f"PREDICTION_IO: input {name} is not an input channel")
    for output in prediction["outputs"]:
        if channels.get(output["compare_channel"], {}).get("role") != "observed_output":
            errors.append(f"PREDICTION_IO: output {output['output_id']} compares with non-output channel {output['compare_channel']}")
    envelope = slice_contract["operating_envelope"]["inputs_canonical"]
    if set(envelope) != set(prediction["inputs"]):
        errors.append("ENVELOPE: the operating envelope must bound exactly the prediction inputs")
    for name, pair in envelope.items():
        if not _ranges_ok(pair):
            errors.append(f"RANGE_INVALID: envelope of {name} is not increasing")
    for case in slice_contract["operating_cases"]:
        if channels.get(case["steady_reference_channel"], {}).get("role") != "input":
            errors.append(f"OPERATING_CASE: {case['case_id']} steady reference must be an input channel")
    rules = slice_contract["residual_rules"]
    if not rules["consistent_max_abs_z"] < rules["discrepant_min_abs_z"]:
        errors.append("RESIDUAL_RULES: consistent_max_abs_z must be below discrepant_min_abs_z")
    if rules["rejected_min_discrepant_fraction"] <= rules["consistent_max_discrepant_fraction"]:
        errors.append("RESIDUAL_RULES: rejection fraction must exceed the consistent discrepant fraction")
    reasons = [s["reason"] for s in slice_contract["no_claim_states"]]
    expected = {"missing", "stale", "late", "sensor_fault", "source_outlier", "out_of_range",
                "calibration_invalid", "outside_envelope", "transient", "not_steady", "input_unavailable"}
    if set(reasons) != expected or len(reasons) != len(expected):
        errors.append("NO_CLAIM_STATES: every no-claim reason must be defined exactly once")
    if slice_contract["timebase_requirements"]["max_inter_channel_skew_s"] >= min(c["nominal_period_s"] for c in channels.values()):
        errors.append("TIMEBASE_REQUIREMENT: skew tolerance must be shorter than the fastest channel period")
    for path in (slice_contract["programme_binding"]["programme_file"], slice_contract["twin_reference"]["twin_record"],
                 slice_contract["vehicle"]["variant_source"], prediction["model_card"]):
        if not (ROOT / path).is_file():
            errors.append(f"REFERENCE_MISSING: {path}")
    programme_path = ROOT / slice_contract["programme_binding"]["programme_file"]
    if programme_path.is_file():
        programme = load_json(programme_path)
        binding = slice_contract["programme_binding"]
        if programme.get("program_id") != binding["program_id"]:
            errors.append("PROGRAMME_BINDING: program_id differs from the programme file")
        if binding["zone_id"] not in {z.get("zone_id") for z in programme.get("zones", [])}:
            errors.append("PROGRAMME_BINDING: zone_id is not a zone of the programme")
        if binding["acquisition_contract_id"] not in {a.get("contract_id") for a in programme.get("acquisition_contracts", [])}:
            errors.append("PROGRAMME_BINDING: acquisition_contract_id is not in the programme")
        if slice_contract["vehicle"]["variant"] not in programme.get("vehicle", {}).get("variants", []):
            errors.append("PROGRAMME_BINDING: variant is not a variant of the programme")
    twin_path = ROOT / slice_contract["twin_reference"]["twin_record"]
    if twin_path.is_file() and load_json(twin_path).get("twin_id") != slice_contract["twin_reference"]["twin_id"]:
        errors.append("TWIN_REFERENCE: twin_id differs from the twin record")
    return errors


def check_model(model_card: dict, slice_contract: dict) -> list[str]:
    errors = []
    if model_card["contract_id"] != slice_contract["contract_id"]:
        errors.append("CONTRACT_MISMATCH: model card is written for another contract")
    prediction = slice_contract["prediction"]
    if [i["channel_id"] for i in model_card["inputs"]] != prediction["inputs"]:
        errors.append("MODEL_IO_MISMATCH: model inputs differ from the contract prediction inputs")
    if [o["output_id"] for o in model_card["outputs"]] != [o["output_id"] for o in prediction["outputs"]]:
        errors.append("MODEL_IO_MISMATCH: model outputs differ from the contract prediction outputs")
    quantities = {q["quantity_id"]: q["canonical_unit"] for q in slice_contract["quantities"]}
    channels = {c["channel_id"]: c for c in slice_contract["channels"]}
    compare = {o["output_id"]: o["compare_channel"] for o in prediction["outputs"]}
    for item in model_card["inputs"]:
        channel = channels.get(item["channel_id"])
        if channel and quantities.get(channel["quantity_id"]) != item["unit"]:
            errors.append(f"MODEL_IO_MISMATCH: input {item['channel_id']} must be in the canonical unit")
    equations = {e["equation_id"] for e in model_card["equations"]}
    for item in model_card["outputs"]:
        channel = channels.get(compare.get(item["output_id"], ""))
        if channel and quantities.get(channel["quantity_id"]) != item["unit"]:
            errors.append(f"MODEL_IO_MISMATCH: output {item['output_id']} must be in the canonical unit")
        if item["equation"] not in equations:
            errors.append(f"MODEL_IO_MISMATCH: output {item['output_id']} names an undefined equation")
    return errors


def check_parameters(parameter_set: dict, model_card: dict) -> list[str]:
    errors = []
    if (parameter_set["model_id"], parameter_set["model_revision"]) != (model_card["model_id"], model_card["model_revision"]):
        errors.append("MODEL_BINDING_MISMATCH: parameter set is written for another model revision")
    names = [p["name"] for p in parameter_set["parameters"]]
    if len(names) != len(set(names)) or set(names) != set(model_card["parameters_required"]):
        errors.append("PARAMETER_SET: parameters must match parameters_required exactly once each")
    if parameter_set["data_class"] == "synthetic" and "synthetic" not in parameter_set["statement"].lower():
        errors.append("SYNTHETIC_LABEL: a synthetic parameter set must say so in its statement")
    return errors


def check_register(register: dict) -> list[str]:
    errors = []
    ids = [i["instrument_id"] for i in register["instruments"]]
    if len(ids) != len(set(ids)):
        errors.append("CALIBRATION_REGISTER: duplicate instrument_id")
    for instrument in register["instruments"]:
        if instrument["valid_from_utc"] >= instrument["valid_until_utc"]:
            errors.append(f"CALIBRATION_REGISTER: {instrument['instrument_id']} validity window is empty")
        if not _ranges_ok(instrument["range"]):
            errors.append(f"RANGE_INVALID: {instrument['instrument_id']} range is not increasing")
        if register["data_class"] == "measured" and instrument["certificate_status"] != "private_certificate_hashed":
            errors.append(f"CALIBRATION_REGISTER: measured instrument {instrument['instrument_id']} needs a hashed private certificate")
        if register["data_class"] == "synthetic" and instrument["certificate_status"] != "synthetic_no_certificate":
            errors.append(f"CALIBRATION_REGISTER: synthetic instrument {instrument['instrument_id']} cannot cite a certificate")
    if register["data_class"] == "synthetic" and "SYNTHETIC" not in register["statement"]:
        errors.append("SYNTHETIC_LABEL: a synthetic register must say SYNTHETIC in its statement")
    return errors


def check_observations(observations: dict, slice_contract: dict, model_card: dict, parameter_set: dict,
                       register: dict) -> list[str]:
    errors = []
    if (observations["contract_id"], observations["contract_revision"]) != (slice_contract["contract_id"], slice_contract["contract_revision"]):
        errors.append("CONTRACT_MISMATCH: observation set is bound to another contract revision")
    if observations["specimen_id"] != slice_contract["specimen"]["specimen_id"]:
        errors.append("SPECIMEN_MISMATCH: observation specimen differs from the contract specimen")
    if observations["synchronisation_mode"] != "offline_replay":
        errors.append("MODE_NOT_IMPLEMENTED: only offline_replay is implemented; live synchronisation is blocked")

    provenance = observations["provenance"]
    inline = [c for c in observations["channels"] if "samples" in c]
    if provenance["data_class"] == "synthetic":
        if "SYNTHETIC" not in provenance["label"] or provenance["generator"] is None:
            errors.append("SYNTHETIC_LABEL: synthetic observations need a SYNTHETIC label and their generator")
        if provenance["raw_data"]["storage"] != "inline_synthetic" or len(inline) != len(observations["channels"]):
            errors.append("RAW_DATA_POLICY: synthetic observations are stored inline")
        if provenance["source_rights"]["publication"] != "public_synthetic":
            errors.append("RAW_DATA_POLICY: synthetic observations are published as public_synthetic")
    else:
        if inline:
            errors.append("RAW_DATA_POLICY: measured samples must stay in the private evidence release (use samples_ref)")
        if provenance["raw_data"]["storage"] != "private_evidence_release":
            errors.append("RAW_DATA_POLICY: measured observations must declare private_evidence_release storage")
        if provenance["source_rights"]["contributor_consent_ref"] is None:
            errors.append("SOURCE_RIGHTS: measured observations need a contributor consent reference")
        if provenance["source_rights"]["publication"] == "public_synthetic":
            errors.append("SOURCE_RIGHTS: measured observations cannot be published as synthetic")
        if register["data_class"] != "measured" or parameter_set["data_class"] != "measured":
            errors.append("RAW_DATA_POLICY: measured observations need a measured register and sourced parameters")

    binding = observations["model_binding"]
    if (binding["model_id"], binding["model_revision"]) != (model_card["model_id"], model_card["model_revision"]):
        errors.append("MODEL_BINDING_MISMATCH: observation set names another model revision")
    if binding["model_card_sha256"] != canonical_sha256(model_card):
        errors.append("MODEL_BINDING_MISMATCH: model_card_sha256 does not match the model card")
    if binding["parameter_set_id"] != parameter_set["parameter_set_id"] or binding["parameter_set_sha256"] != canonical_sha256(parameter_set):
        errors.append("MODEL_BINDING_MISMATCH: parameter set id or sha256 does not match")
    reg_binding = observations["calibration_register"]
    if reg_binding["register_id"] != register["register_id"] or reg_binding["sha256"] != canonical_sha256(register):
        errors.append("CALIBRATION_REGISTER_MISMATCH: register id or sha256 does not match")

    timebase = observations["timebase"]
    needs = slice_contract["timebase_requirements"]
    if timebase["resolution_s"] > needs["max_resolution_s"]:
        errors.append("TIMEBASE_REQUIREMENT: timebase resolution is coarser than the contract allows")
    if timebase["max_inter_channel_skew_s"] > needs["max_inter_channel_skew_s"]:
        errors.append("TIMEBASE_REQUIREMENT: declared inter-channel skew exceeds the contract tolerance")
    if timebase["drift_bound_ppm"] > needs["max_drift_ppm"]:
        errors.append("TIMEBASE_REQUIREMENT: declared drift exceeds the contract tolerance")

    cases = {c["case_id"]: c for c in slice_contract["operating_cases"]}
    case_log = observations["operating_case"]
    case = cases.get(case_log["case_id"])
    if case is None:
        errors.append(f"OPERATING_CASE: {case_log['case_id']} is not a contract operating case")
    else:
        previous_end = -math.inf
        for start, end in case_log["steady_windows_s"]:
            if not (0 <= start < end <= case_log["duration_s"]) or start < previous_end:
                errors.append("OPERATING_CASE: steady windows must be ordered, disjoint and inside the session")
            elif end - start < case["min_steady_window_s"]:
                errors.append(f"OPERATING_CASE: steady window [{start}, {end}] is shorter than {case['min_steady_window_s']} s")
            previous_end = end

    contract_channels = {c["channel_id"]: c for c in slice_contract["channels"]}
    quantities = {q["quantity_id"]: q for q in slice_contract["quantities"]}
    stations = {s["station_id"]: s for s in slice_contract["stations"]}
    frames = {f["frame_id"] for f in slice_contract["frames"]}
    instruments = {i["instrument_id"]: i for i in register["instruments"]}
    seen = [c["channel_id"] for c in observations["channels"]]
    if sorted(seen) != sorted(contract_channels) or len(seen) != len(set(seen)):
        errors.append("CHANNEL_SET: observation channels must be exactly the contract channels, once each")
    for channel in observations["channels"]:
        name = channel["channel_id"]
        spec = contract_channels.get(name)
        if spec is None:
            continue
        if channel["timebase_id"] != timebase["timebase_id"]:
            errors.append(f"TIMEBASE_MISMATCH: channel {name} is on timebase {channel['timebase_id']}, not {timebase['timebase_id']}")
        quantity = quantities[spec["quantity_id"]]
        if channel["unit"] not in quantity["accepted_units"]:
            errors.append(f"UNIT_NOT_ACCEPTED: channel {name} unit {channel['unit']} is not accepted for {quantity['quantity_id']}")
        if channel["nominal_period_s"] > spec["nominal_period_s"]:
            errors.append(f"CADENCE: channel {name} samples slower than the contract period")
        instrument = instruments.get(channel["instrument_id"])
        if instrument is None or instrument["calibration_id"] != channel["calibration_id"]:
            errors.append(f"CALIBRATION_UNKNOWN: channel {name} cites an instrument or calibration absent from the register")
        elif instrument["unit"] != channel["unit"]:
            errors.append(f"CALIBRATION_UNIT_MISMATCH: channel {name} is in {channel['unit']} but its calibration is in {instrument['unit']}")
        mount = channel["mount"]
        station = stations.get(spec["station_id"]) if spec["station_id"] else None
        if station is not None and mount is None:
            errors.append(f"FRAME_STATION: channel {name} needs a mount to check station {station['station_id']}")
        if mount is not None:
            if mount["parent_frame_id"] not in frames:
                errors.append(f"FRAME_UNKNOWN: channel {name} mount parent {mount['parent_frame_id']} is not a contract frame")
            rotation = rotation_errors(mount["rotation_parent_from_sensor"])
            if rotation:
                errors.append(f"FRAME_INVALID: channel {name} rotation {'; '.join(rotation)}")
            elif station is not None:
                if station["frame_id"] != mount["parent_frame_id"]:
                    errors.append(f"FRAME_STATION: channel {name} is mounted in another frame than its station")
                else:
                    errors += [f"FRAME_STATION: channel {name} {m}" for m in station_errors(station, mount_in_parent(mount))]
        if "samples_ref" in channel:
            continue
        for index, sample in enumerate(channel["samples"]):
            value, flag = sample[3], sample[4]
            if (value is None) != (flag == "missing"):
                errors.append(f"SAMPLE_FLAG: channel {name} sample {index}: value is null exactly when the flag is missing")
    return errors


# --------------------------------------------------------------------------- bundle and fixtures

def validate_documents(documents: dict[str, Any]) -> list[str]:
    """Validate one complete bundle, given as {document_kind: document}."""
    validator = SchemaValidator(load_json(SCHEMA_PATH))
    errors: list[str] = []
    for kind in BUNDLE:
        document = documents[kind]
        if not isinstance(document, dict) or document.get("document_kind") != kind:
            errors.append(f"SCHEMA: {kind}: document_kind must be {kind}")
            continue
        errors += [e.replace("SCHEMA: ", f"SCHEMA: {kind}", 1) for e in validator.validate_kind(document)]
        errors += privacy_errors(document, kind)
    if errors:
        return errors
    slice_contract, model_card = documents["slice_contract"], documents["model_card"]
    parameter_set, register = documents["parameter_set"], documents["calibration_register"]
    errors += check_slice(slice_contract)
    errors += check_model(model_card, slice_contract)
    errors += check_parameters(parameter_set, model_card)
    errors += check_register(register)
    errors += check_observations(documents["observation_set"], slice_contract, model_card, parameter_set, register)
    return errors


def load_bundle(paths: dict[str, Path] | None = None) -> dict[str, Any]:
    return {kind: load_json(path) for kind, path in (paths or BUNDLE).items()}


def error_codes(errors: list[str]) -> list[str]:
    return sorted({error.split(":", 1)[0] for error in errors})


def apply_patch(document: Any, operations: list[dict]) -> Any:
    """Apply a JSON Patch subset (add, replace, remove) to a deep copy."""
    result = copy.deepcopy(document)
    for operation in operations:
        tokens = [t.replace("~1", "/").replace("~0", "~") for t in operation["path"].split("/")[1:]]
        parent = result
        for token in tokens[:-1]:
            parent = parent[int(token)] if isinstance(parent, list) else parent[token]
        last = tokens[-1]
        op = operation["op"]
        if isinstance(parent, list):
            index = len(parent) if last == "-" else int(last)
            if op == "add":
                parent.insert(index, operation["value"])
            elif op == "replace":
                parent[index] = operation["value"]
            elif op == "remove":
                del parent[index]
            else:
                raise ValueError(f"unsupported patch operation {op}")
        else:
            if op in {"add", "replace"}:
                if op == "replace" and last not in parent:
                    raise KeyError(f"replace of a missing member {operation['path']}")
                parent[last] = operation["value"]
            elif op == "remove":
                del parent[last]
            else:
                raise ValueError(f"unsupported patch operation {op}")
    return result


def run_invalid_fixture(fixture: dict, base: dict[str, Any]) -> list[str]:
    documents = dict(base)
    documents[fixture["target"]] = apply_patch(base[fixture["target"]], fixture["patch"])
    return validate_documents(documents)


def check_all() -> dict:
    base = load_bundle()
    result = {"bundle_errors": validate_documents(base), "fixtures": []}
    for path in sorted(INVALID_FIXTURES.glob("*.json")):
        fixture = load_json(path)
        errors = run_invalid_fixture(fixture, base)
        codes = error_codes(errors)
        result["fixtures"].append({
            "fixture": path.relative_to(ROOT).as_posix(),
            "expected_codes": sorted(fixture["expected_codes"]),
            "codes": codes,
            "passed": bool(errors) and codes == sorted(fixture["expected_codes"]),
            "errors": errors,
        })
    result["passed"] = not result["bundle_errors"] and bool(result["fixtures"]) and all(f["passed"] for f in result["fixtures"])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = parser.parse_args(argv)
    result = check_all()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for error in result["bundle_errors"]:
            print(f"bundle: {error}", file=sys.stderr)
        for fixture in result["fixtures"]:
            state = "ok" if fixture["passed"] else "FAILED"
            print(f"{state}: {fixture['fixture']} rejected with {', '.join(fixture['codes']) or 'nothing'}"
                  f" (expected {', '.join(fixture['expected_codes'])})")
        print("operational twin contract: " + ("valid" if result["passed"] else "INVALID"))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
