#!/usr/bin/env python3
"""Build a logical cooling-system twin and bounded reduced-order calculations."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re

STUDY = Path(__file__).resolve().parents[1]
ROOT = STUDY.parents[1]
UNITS = {
    "engine_rpm": "rpm", "belt_speed_ratio": "1", "belt_slip_fraction": "1",
    "gear_speed_ratio": "1", "rotor_diameter": "m", "blade_count": "1",
    "rotor_inertia": "kg*m2", "rotor_acceleration": "rad/s2",
    "residual_unbalance": "kg*m", "air_density": "kg/m3", "air_cp": "J/(kg*K)",
    "branch_inlet_temperature": "degC", "common_resistance": "Pa*s2/m6",
    "drive_efficiency": "1", "input_pulley_pitch_radius": "m", "thermal_step": "s",
    "map_rotor_rpm": "rpm", "map_air_density": "kg/m3",
    "fan_map": "Q_m3_s,dp_total_total_Pa,eta_total_total",
    "resistance": "Pa*s2/m6", "solid_heat_load": "W", "ua": "W/K",
    "thermal_capacity": "J/K", "initial_temperature": "degC",
}


class MissingData(ValueError):
    pass


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Finite numeric value required")
    return float(value)


def positive(value):
    value = finite(value)
    if value <= 0:
        raise ValueError("Positive value required")
    return value


def nonnegative(value):
    value = finite(value)
    if value < 0:
        raise ValueError("Non-negative value required")
    return value


class Inputs:
    def __init__(self, case):
        self.case = case
        self.synthetic = case["purpose"] == "synthetic_verification"
        self.hypothetical = case["purpose"] == "hypothesis_screen"
        if case["purpose"] not in ("specimen_model", "synthetic_verification", "hypothesis_screen"):
            raise ValueError("Unknown calculation purpose")
        self.evidence = {e["id"]: e for e in case["evidence"]}
        if len(self.evidence) != len(case["evidence"]):
            raise ValueError("Duplicate evidence identifier")

    def attest(self, refs):
        if not refs:
            raise MissingData("Independent evidence is missing")
        for ref in refs:
            if ref not in self.evidence:
                raise ValueError("Unknown evidence identifier")
            item = self.evidence[ref]
            if not item.get("locator"):
                raise ValueError("Evidence locator required")
            if self.synthetic:
                if item["kind"] != "synthetic_fixture":
                    raise ValueError("Synthetic case must use fixture evidence")
            elif self.hypothetical:
                if item["kind"] != "assumption" or not item.get("rejection_test"):
                    raise ValueError("Hypothesis inputs require an assumption and rejection test")
            else:
                if not self.case.get("specimen_id"):
                    raise MissingData("Exact specimen identity is missing")
                if item["kind"] not in ("independent_measurement", "qualified_solver_result"):
                    raise ValueError("Synthetic or scan-derived evidence cannot qualify specimen inputs")
                if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256") or ""):
                    raise ValueError("Pinned evidence SHA-256 required")

    def get(self, name, records=None, table=False):
        record = (self.case["parameters"] if records is None else records)[name]
        if record["unit"] != UNITS[name]:
            raise ValueError("Input unit mismatch: " + name)
        if record["value"] is None:
            raise MissingData("Missing input: " + name)
        if record.get("uncertainty") is None:
            raise MissingData("Missing uncertainty: " + name)
        if table:
            uncertainty = record["uncertainty"]
            if not isinstance(uncertainty, list) or len(uncertainty) != len(record["value"]):
                raise ValueError("Fan-map uncertainties required per row and column")
            for row in uncertainty:
                if len(row) != 3:
                    raise ValueError("Three fan-map uncertainty columns required")
                for value in row:
                    nonnegative(value)
        else:
            nonnegative(record["uncertainty"])
        self.attest(record["evidence_ids"])
        return record["value"] if table else finite(record["value"])


def interpolate(rows, q, column):
    if not rows[0][0] <= q <= rows[-1][0]:
        raise ValueError("Fan-map extrapolation prohibited")
    for a, b in zip(rows, rows[1:]):
        if a[0] <= q <= b[0]:
            return a[column] + (b[column] - a[column]) * (q - a[0]) / (b[0] - a[0])
    raise ValueError("Invalid interpolation interval")


def operating_point(rows, common, resistances):
    """Single monotone fan map; series loss plus parallel quadratic branches."""
    if len(rows) < 2:
        raise ValueError("At least two fan-map points required")
    rows = [[finite(v) for v in row] for row in rows]
    if any(len(row) != 3 or row[0] < 0 or row[1] < 0 or not 0 < row[2] <= 1 for row in rows):
        raise ValueError("Invalid Q/total-pressure/total-efficiency map")
    if any(b[0] <= a[0] or b[1] > a[1] for a, b in zip(rows, rows[1:])):
        raise ValueError("Map must have increasing Q and non-increasing pressure")
    common = nonnegative(common)
    weights = [1 / math.sqrt(positive(r)) for r in resistances]
    if not weights:
        raise MissingData("Measured branch topology and resistances are missing")
    parallel = 1 / sum(weights) ** 2
    equivalent = common + parallel
    lo, hi = rows[0][0], rows[-1][0]
    residual = lambda q: interpolate(rows, q, 1) - equivalent * q * q
    if residual(lo) < 0 or residual(hi) > 0:
        raise MissingData("Operating point outside measured fan-map range")
    for _ in range(100):
        mid = (lo + hi) / 2
        if residual(mid) > 0:
            lo = mid
        else:
            hi = mid
    q = (lo + hi) / 2
    pressure = interpolate(rows, q, 1)
    eta = interpolate(rows, q, 2)
    flows = [q * w / sum(weights) for w in weights]
    return {"volume_flow_m3_s": q, "total_pressure_rise_pa": pressure,
            "fan_shaft_power_w": q * pressure / eta, "total_efficiency": eta,
            "branch_volume_flow_m3_s": flows, "parallel_pressure_loss_pa": parallel * q * q,
            "series_pressure_loss_pa": common * q * q,
            "mass_balance_residual_m3_s": q - sum(flows),
            "pressure_balance_residual_pa": residual(q)}


def thermal_step(flow, density, cp, ua, capacity, heat, inlet, initial, dt):
    """Constant-flow lump, single-pass effectiveness, fixed load over one step."""
    mass_cp = positive(flow) * positive(density) * positive(cp)
    conductance = mass_cp * -math.expm1(-positive(ua) / mass_cp)
    capacity, heat = positive(capacity), nonnegative(heat)
    inlet, initial, dt = finite(inlet), finite(initial), nonnegative(dt)
    if min(inlet, initial) <= -273.15:
        raise ValueError("Temperature must exceed absolute zero")
    steady = inlet + heat / conductance
    final = steady + (initial - steady) * math.exp(-conductance * dt / capacity)
    exchanged = conductance * (final - inlet)
    return {"steady_solid_temperature_deg_c": steady, "solid_temperature_after_step_deg_c": final,
            "air_outlet_temperature_after_step_deg_c": inlet + exchanged / mass_cp,
            "thermal_time_constant_s": capacity / conductance,
            "steady_air_temperature_rise_k": heat / mass_cp,
            "transient_heat_to_air_w": exchanged}


def calculate(case):
    data = Inputs(case)
    models = {}

    def run(name, operation):
        try:
            result = operation()
            # Reject numeric overflow before creating any result artifact.
            json.dumps(result, allow_nan=False)
            status = ("hypothesis_calculation" if data.hypothetical else
                      "synthetic_calculation" if data.synthetic else "conditional_prediction")
            models[name] = {"status": status,
                            "values": result, "missing": []}
        except MissingData as error:
            models[name] = {"status": "blocked_missing_inputs", "values": None, "missing": [str(error)]}

    def previous(name):
        if models[name]["values"] is None:
            raise MissingData("Dependency blocked: " + name)
        return models[name]["values"]

    def speeds():
        slip = nonnegative(data.get("belt_slip_fraction"))
        if slip >= 1:
            raise ValueError("Belt slip must be less than one")
        ratio = positive(data.get("gear_speed_ratio"))
        rpm_in = nonnegative(data.get("engine_rpm")) * positive(data.get("belt_speed_ratio")) * (1 - slip)
        return {"input_rpm": rpm_in, "rotor_rpm": rpm_in * ratio}

    def rotor():
        rpm = previous("speeds")["rotor_rpm"]
        blades = positive(data.get("blade_count"))
        if not blades.is_integer():
            raise ValueError("Integer blade count required")
        return {"tip_speed_m_s": math.pi * positive(data.get("rotor_diameter")) * rpm / 60,
                "blade_passing_frequency_hz": blades * rpm / 60}

    def inertia():
        omega = previous("speeds")["rotor_rpm"] * 2 * math.pi / 60
        j = positive(data.get("rotor_inertia"))
        return {"rotor_kinetic_energy_j": 0.5 * j * omega ** 2,
                "rotor_acceleration_torque_nm": j * data.get("rotor_acceleration"),
                "unbalance_force_amplitude_n": nonnegative(data.get("residual_unbalance")) * omega ** 2,
                "rotor_inertia_reflected_to_input_kg_m2": j * positive(data.get("gear_speed_ratio")) ** 2}

    def airflow():
        rpm = previous("speeds")["rotor_rpm"]
        density = positive(data.get("air_density"))
        if not math.isclose(positive(data.get("map_rotor_rpm")), rpm, rel_tol=1e-9, abs_tol=1e-9):
            raise MissingData("Fan map is not at the case rotor speed; no affinity extrapolation")
        if not math.isclose(positive(data.get("map_air_density")), density, rel_tol=1e-9, abs_tol=1e-9):
            raise MissingData("Fan map density differs from the case")
        if case["pressure_basis"] != "total_to_total":
            raise ValueError("Only consistently defined total-to-total pressure is implemented")
        stations = case.get("pressure_stations")
        if not stations or len(stations) != 2 or not all(isinstance(s, str) and s for s in stations) or stations[0] == stations[1]:
            raise MissingData("Distinct matched fan/network pressure stations are missing")
        if case["air_topology_confirmed"] is not True:
            raise MissingData("Actual air-network topology is unconfirmed")
        data.attest(case["air_topology_evidence_ids"])
        ids = [b["id"] for b in case["branches"]]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate branch identifier")
        rs = [data.get("resistance", b["parameters"]) for b in case["branches"]]
        result = operating_point(data.get("fan_map", table=True), data.get("common_resistance"), rs)
        result["mass_flow_kg_s"] = density * result["volume_flow_m3_s"]
        result["branch_ids"] = ids
        return result

    def drive():
        flow, speed = previous("airflow"), previous("speeds")
        eta = positive(data.get("drive_efficiency"))
        if eta > 1:
            raise ValueError("Drive efficiency exceeds one")
        omega_in = positive(speed["input_rpm"]) * 2 * math.pi / 60
        omega_out = positive(speed["rotor_rpm"]) * 2 * math.pi / 60
        input_power = flow["fan_shaft_power_w"] / eta
        torque = input_power / omega_in
        return {"steady_fan_torque_nm": flow["fan_shaft_power_w"] / omega_out,
                "steady_drive_input_power_w": input_power,
                "steady_drive_loss_w": input_power - flow["fan_shaft_power_w"],
                "steady_drive_input_torque_nm": torque,
                "belt_tension_difference_n": torque / positive(data.get("input_pulley_pitch_radius"))}

    def thermal():
        flow = previous("airflow")
        results = {}
        for b, q in zip(case["branches"], flow["branch_volume_flow_m3_s"]):
            if b["role"] == "leakage":
                continue
            if b["role"] != "cooled_zone":
                raise ValueError("Unknown thermal branch role")
            records = b["parameters"]
            results[b["id"]] = thermal_step(q, data.get("air_density"), data.get("air_cp"),
                data.get("ua", records), data.get("thermal_capacity", records), data.get("solid_heat_load", records),
                data.get("branch_inlet_temperature"), data.get("initial_temperature", records), data.get("thermal_step"))
        if not results:
            raise MissingData("Cooled-zone thermal data missing")
        return results

    for name, operation in (("speeds", speeds), ("rotor_kinematics", rotor), ("inertia_and_unbalance", inertia),
                            ("airflow", airflow), ("steady_drive_budget", drive), ("thermal", thermal)):
        run(name, operation)
    return {"case_id": case["id"], "purpose": case["purpose"], "models": models,
            "predictions_are_specimen_characteristics": False,
            "evidence_artifact_contents_independently_reviewed": False,
            "input_uncertainty_propagation_implemented": False,
            "input_evidence_sha256": sorted({e['sha256'] for e in case['evidence'] if e.get('sha256')}),
            "digital_twin_validated": False, "manufacturing_release_allowed": False}


def logical_usda(definition, contract):
    """Relationship-only stage: no CAD conversion, geometry, mass or pose defaults."""
    name = lambda ident: "n_" + re.sub(r"[^A-Za-z0-9_]", "_", ident)
    ids = [c["id"] for c in definition["components"]]
    if len(set(ids)) != len(ids) or len({name(i) for i in ids}) != len(ids):
        raise ValueError("Duplicate USD component name")
    q = lambda text: json.dumps(text, ensure_ascii=False)
    lines = ['#usda 1.0', '(', '    defaultPrim = "CoolingSystem"', '    metersPerUnit = 1',
             '    upAxis = "Z"', ')', 'def Scope "CoolingSystem"', '{',
             '    custom string twin:status = "logical_unpositioned_blueprint"',
             '    custom bool twin:physicalAssemblyVerified = false',
             '    custom bool twin:scanScaleVerified = false', '    def Scope "Components"', '    {']
    for c in definition["components"]:
        lines += [f'        def Scope "{name(c["id"])}"', '        {',
                  f'            custom string twin:componentId = {q(c["id"])}',
                  f'            custom string displayName = {q(c["label_fr"])}',
                  '            custom bool twin:geometryAdmitted = false', '        }']
    lines += ['    }', '    def Scope "Interfaces"', '    {']
    for i in contract["interfaces"]:
        if any(c not in ids for c in i["components"]):
            raise ValueError("Unresolved component graph reference")
        sides = ', '.join(f'</CoolingSystem/Components/{name(c)}>' for c in i["components"])
        lines += [f'        def Scope "{name(i["id"])}"', '        {', f'            rel twin:sides = [{sides}]',
                  f'            custom string twin:interfaceId = {q(i["id"])}',
                  '            custom bool twin:measuredInterfaceAdmitted = false', '        }']
    lines += ['    }', '}', '']
    return '\n'.join(lines)


def build(case_path, output):
    case_path, output = case_path.resolve(), output.resolve()
    if output.exists() or (output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / 'work')):
        raise ValueError("Use a new private output directory")
    case_bytes = case_path.read_bytes()
    case = json.loads(case_bytes, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    report = calculate(case)
    definition = json.loads((STUDY / 'system-definition.json').read_text())
    contract = json.loads((STUDY / 'interface-contract.json').read_text())
    usd = logical_usda(definition, contract)
    report.update({"components": len(definition["components"]), "interfaces": len(contract["interfaces"]),
                   "measured_interfaces_verified": sum(i['verified'] is True for i in contract['interfaces']),
                   "positioned_assembly_complete": False, "geometry_conversion_executed": False,
                   "source_scan_geometry_loaded": False, "case_sha256": hashlib.sha256(case_bytes).hexdigest(),
                   "parameter_readiness": {k: {"value_present": v['value'] is not None,
                     "unit": v['unit'], "evidence_ids": v['evidence_ids'], "uncertainty_present": v['uncertainty'] is not None}
                     for k, v in case['parameters'].items()},
                   "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                   "model_input_sha256": {p: hashlib.sha256((STUDY / p).read_bytes()).hexdigest()
                     for p in ('system-definition.json', 'interface-contract.json', 'solver-handoff.json', 'measurement-contract.json')}})
    text = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    output.mkdir(parents=True, mode=0o700)
    (output / 'readiness-and-predictions.json').write_text(text)
    (output / 'system-logical.usda').write_text(usd)
    cards = ''.join(f'<section><h2>{html.escape(k)}</h2><p>{html.escape(v["status"])}</p>'
                    f'<pre>{html.escape(json.dumps(v["values"] if v["values"] is not None else v["missing"],indent=2))}</pre></section>'
                    for k, v in report['models'].items())
    rows = ''.join(f'<tr><td>{html.escape(i["id"])}</td><td>{html.escape(" ↔ ".join(i["components"]))}</td>'
                   '<td>Mesures à établir</td></tr>' for i in contract['interfaces'])
    page = '<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
    page += '<title>Système 935 — préparation du jumeau</title><style>body{font:16px system-ui;background:#101923;color:#edf3f8;max-width:1100px;margin:32px auto;padding:20px}section{background:#1c2b3a;padding:14px;margin:12px 0;border-radius:8px}td,th{padding:9px;border-bottom:1px solid #445566;text-align:left}pre{white-space:pre-wrap}strong{color:#ffc56d}</style>'
    page += '<h1>Système horizontal 935</h1><p><strong>Base logique du jumeau — assemblage, interfaces et performances physiques à qualifier.</strong></p>'
    page += f'<p>Cas : {html.escape(case["id"])} · {html.escape(case["purpose"])}. Les nombres synthétiques ou hypothétiques concernent uniquement le scénario choisi.</p>'
    page += cards + '<h2>Interfaces du système</h2><table><tr><th>Interface</th><th>Éléments</th><th>État</th></tr>' + rows + '</table></html>'
    (output / 'review.html').write_text(page)
    for p in output.iterdir():
        p.chmod(0o600)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.case, args.output)
    ready = sum(m['values'] is not None for m in result['models'].values())
    print(f"Logical twin built: {result['components']} components/boundaries, {result['interfaces']} interfaces, {ready}/6 model groups evaluated; no physical twin validation")
