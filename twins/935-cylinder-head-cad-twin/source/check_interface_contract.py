#!/usr/bin/env python3
"""Check the 935 head twin against its interface contract (#694).

Reads params/interface-contract.json and, for each quantity, the twin's own number named under
twin_nominal_not_evidence (a params file and a key). Reports pass, fail or not_checkable per quantity:

- not_checkable when the contract value is null, when the twin holds no number or no comparable number, when
  no acceptance threshold is committed, or when the threshold is less than twice the stated uncertainty;
- pass when |twin - value| <= threshold for a scalar, the distance between the points for a point, the angle
  between the axes for a direction (sign ignored), and equality for a designation or a count;
- fail otherwise.

Independence: this script reads JSON only and imports the standard library only. It shares no code with the
scripts that fitted the datums and features or built the body (fit_frame.py, occupancy.py, fit_features.py,
twin_common.py and the rest): model output must not supply its own inspection evidence. The twin's numbers are
what is checked, never what a value is checked with.

The contract is refused, and nothing is written, when a value has no source or no uncertainty, when a source
is the twin itself, when a value equals the twin's own number, or when a key or a hypothesis does not resolve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

SCHEMA = "935-cad-twin-interface-contract-check/1"
CONTRACT_SCHEMA = "935-cad-twin-interface-contract/1"
TWIN = Path(__file__).resolve().parents[1]

# Unit of the deviation for each kind; None for kinds compared by equality.
KINDS = {
    "length": "mm", "diameter": "mm", "level": "mm", "flatness": "mm", "tolerance": "mm", "point": "mm",
    "angle": "deg", "direction": "deg", "designation": None, "count": None,
}
SCALAR = {"length", "diameter", "level", "flatness", "angle"}
EXACT = {"designation", "count"}
SCALE_FREE = {"angle", "direction", "designation", "count"}
BLOCKER_FIELDS = ("fill_with", "requires", "compare_requires")
# A source may not be the twin itself: its params, code, media, register or private work folder.
TWIN_OWN_PREFIXES = ("params/", "source/", "media/", "work/", "hypotheses.json")
TWIN_OWN_MARKERS = ("935-cylinder-head-cad-twin/params/", "935-cylinder-head-cad-twin/source/",
                    "935-cylinder-head-cad-twin/media/", "935-cylinder-head-cad-twin/hypotheses.json", "935-cad-twin/")

NOT_MEASURED = "value null: nothing is measured or documented"


class ContractError(ValueError):
    """The contract cannot be checked as written."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve(doc, key):
    """Follow a key: strings and integers index; a one-field object selects the one list item with that field."""

    cur = doc
    for seg in key:
        if isinstance(seg, dict):
            if len(seg) != 1 or not isinstance(cur, list):
                raise ContractError(f"bad selector {seg!r} in {key!r}")
            (field, want), = seg.items()
            hits = [x for x in cur if isinstance(x, dict) and x.get(field) == want]
            if len(hits) != 1:
                raise ContractError(f"selector {seg!r} matches {len(hits)} items in {key!r}")
            cur = hits[0]
        elif isinstance(seg, int) and not isinstance(seg, bool):
            if not isinstance(cur, list) or not -len(cur) <= seg < len(cur):
                raise ContractError(f"index {seg} out of range in {key!r}")
            cur = cur[seg]
        elif isinstance(seg, str):
            if not isinstance(cur, dict) or seg not in cur:
                raise ContractError(f"no field {seg!r} in {key!r}")
            cur = cur[seg]
        else:
            raise ContractError(f"bad key segment {seg!r} in {key!r}")
    return cur


class Params:
    """The twin's committed params files, read once each, with their hashes."""

    def __init__(self, twin_dir: Path):
        self.twin_dir = Path(twin_dir)
        self.docs: dict[str, object] = {}
        self.hashes: dict[str, str] = {}

    def doc(self, rel: str):
        if not isinstance(rel, str) or not rel.startswith("params/") or ".." in Path(rel).parts:
            raise ContractError(f"twin numbers come from params/ only, not {rel!r}")
        if rel not in self.docs:
            path = self.twin_dir / rel
            if not path.is_file():
                raise ContractError(f"missing params file {rel}")
            data = path.read_bytes()
            self.hashes[rel] = sha256_bytes(data)
            self.docs[rel] = json.loads(data)
        return self.docs[rel]

    def number(self, ref: dict):
        doc = self.doc(ref.get("params"))
        derive = ref.get("derive")
        if derive is None:
            return resolve(doc, ref["key"])
        if derive == "distance":
            a, b = (resolve(doc, k) for k in ref["keys"])
            if not (is_vector(a) and is_vector(b) and len(a) == len(b)):
                raise ContractError(f"distance needs two points of one dimension: {ref['keys']!r}")
            return round(math.dist(a, b), 4)
        raise ContractError(f"unknown derivation {derive!r}")


def is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def is_vector(x) -> bool:
    return isinstance(x, list) and len(x) >= 2 and all(is_number(v) for v in x)


def same(a, b) -> bool:
    if is_number(a) and is_number(b):
        return math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def deviation(kind: str, twin, value) -> float:
    """|twin - value| in the unit of the deviation."""

    if kind in SCALAR:
        if not (is_number(twin) and is_number(value)):
            raise ContractError(f"{kind} compares two numbers")
        return abs(float(twin) - float(value))
    if kind == "point":
        if not (is_vector(twin) and is_vector(value) and len(twin) == len(value)):
            raise ContractError("a point compares two vectors of one dimension")
        return math.dist(twin, value)
    if kind == "direction":
        if not (is_vector(twin) and is_vector(value) and len(twin) == len(value) == 3):
            raise ContractError("a direction compares two 3-vectors")
        na, nb = math.hypot(*twin), math.hypot(*value)
        if na == 0 or nb == 0:
            raise ContractError("a direction cannot be a zero vector")
        cos = abs(sum(x * y for x, y in zip(twin, value))) / (na * nb)
        return math.degrees(math.acos(min(1.0, cos)))
    raise ContractError(f"no deviation for kind {kind!r}")


def own_source(source: str) -> bool:
    s = source.strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s.startswith(TWIN_OWN_PREFIXES) or any(m in s for m in TWIN_OWN_MARKERS)


def value_shape_error(q: dict) -> str | None:
    """Why the value cannot stand for its kind, or None."""

    kind, value = q.get("kind"), q.get("value")
    if kind in SCALAR:
        return None if is_number(value) else f"a {kind} value is a number"
    if kind == "point":
        n = len(q.get("components") or []) or None
        ok = is_vector(value) and (n is None or len(value) == n)
        return None if ok else f"a point value is a vector of {n or 'its'} components"
    if kind == "direction":
        return None if is_vector(value) and len(value) == 3 and math.hypot(*value) > 0 else "a direction is a non-zero 3-vector"
    if kind == "tolerance":
        ok = is_vector(value) and len(value) == 2 and value[0] <= value[1]
        return None if ok else "a tolerance is [lower, upper]"
    if kind == "designation":
        return None if isinstance(value, str) and value.strip() else "a designation is text"
    if kind == "count":
        return None if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else "a count is a whole number"
    return None


def quantities(contract: dict):
    for iface in contract.get("interfaces", []):
        for q in iface.get("quantities", []):
            yield iface, q


def validate(contract: dict, hypotheses: dict, params: Params) -> list[str]:
    """Every reason the contract cannot be checked as written."""

    errors = []
    if contract.get("schema") != CONTRACT_SCHEMA:
        errors.append(f"schema is {contract.get('schema')!r}, expected {CONTRACT_SCHEMA!r}")
    codes = set(contract.get("blocker_codes", {}))
    register = {item["id"] for item in hypotheses.get("items", [])}
    iface_ids, q_ids = set(), set()
    for iface in contract.get("interfaces", []):
        iid = iface.get("id")
        if not iid or iid in iface_ids:
            errors.append(f"interface id {iid!r} missing or repeated")
        iface_ids.add(iid)
        if not iface.get("quantities"):
            errors.append(f"{iid}: no quantity")
        for h in iface.get("hypotheses", []):
            if h not in register:
                errors.append(f"{iid}: hypothesis {h!r} is not in hypotheses.json")
    for iface, q in quantities(contract):
        qid = q.get("id")
        where = qid or f"{iface.get('id')}.?"
        if not qid or qid in q_ids:
            errors.append(f"quantity id {qid!r} missing or repeated")
        q_ids.add(qid)
        if qid and not qid.startswith(f"{iface.get('id')}."):
            errors.append(f"{qid}: id does not start with its interface id")
        kind = q.get("kind")
        if kind not in KINDS:
            errors.append(f"{where}: unknown kind {kind!r}")
        for field in ("value", "uncertainty", "source", "threshold", "blocker", "hypothesis",
                      "twin_nominal_not_evidence"):
            if field not in q:
                errors.append(f"{where}: no field {field!r}")
        blocker = q.get("blocker") or {}
        if not blocker.get("fill_with") or not blocker.get("why"):
            errors.append(f"{where}: a blocker names what would fill it and why")
        for field in BLOCKER_FIELDS:
            for code in blocker.get(field, []):
                if code not in codes:
                    errors.append(f"{where}: blocker code {code!r} is not declared")
        hyp = q.get("hypothesis")
        if hyp is not None and hyp not in register:
            errors.append(f"{where}: hypothesis {hyp!r} is not in hypotheses.json")
        value, unc, source, thr = q.get("value"), q.get("uncertainty"), q.get("source"), q.get("threshold")
        if value is not None:
            if not isinstance(source, str) or not source.strip():
                errors.append(f"{where}: a value without a source")
            elif own_source(source):
                errors.append(f"{where}: the source {source!r} is the twin itself")
            if not (is_number(unc) and unc >= 0):
                errors.append(f"{where}: a value without an uncertainty")
            if kind in KINDS:
                shape = value_shape_error(q)
                if shape:
                    errors.append(f"{where}: {shape}")
        elif source is not None or unc is not None:
            errors.append(f"{where}: a source or an uncertainty without a value")
        if thr is not None and not (is_number(thr) and thr > 0):
            errors.append(f"{where}: a threshold is a positive number")
        ref = q.get("twin_nominal_not_evidence")
        if ref is not None:
            try:
                twin = params.number(ref)
            except (ValueError, KeyError, TypeError) as exc:  # ContractError and unreadable JSON
                errors.append(f"{where}: twin number does not resolve: {exc}")
                continue
            if not isinstance(ref.get("comparable"), bool):
                errors.append(f"{where}: twin_nominal_not_evidence states whether it is comparable")
            elif ref["comparable"] and kind in KINDS:
                shape = value_shape_error({**q, "value": twin})
                if shape:
                    errors.append(f"{where}: comparable twin number does not fit: {shape}")
            # A measured number identical to the twin's is a copy. Designations and counts are compared by
            # equality, so for them agreement is the expected outcome and not a sign of copying.
            if value is not None and kind not in EXACT and (
                    same(value, twin) or same(value, ref.get("value_at_writing"))):
                errors.append(f"{where}: the value equals the twin's own number; a twin value may not sit in value")
    return errors


def check_quantity(q: dict, params: Params, scale_open: bool, interface: str | None = None) -> dict:
    kind, value, unc, thr = q["kind"], q["value"], q["uncertainty"], q["threshold"]
    ref = q.get("twin_nominal_not_evidence")
    twin = params.number(ref) if ref is not None else None
    row = {
        "id": q["id"],
        "interface": interface,
        "kind": kind,
        "deviation_unit": KINDS[kind],
        "hypothesis": q.get("hypothesis"),
        "value": value,
        "uncertainty": unc,
        "threshold": thr,
        "twin_number_not_evidence": twin,
        "twin_comparable": None if ref is None else ref["comparable"],
        "twin_changed_since_writing": None if ref is None else not same(twin, ref.get("value_at_writing")),
        "deviation": None,
    }

    def verdict(status, reason):
        row["status"], row["reason"] = status, reason
        if status in ("pass", "fail") and kind not in SCALE_FREE and scale_open:
            row["caveat"] = "the twin's lengths are scan units taken as mm by owner instruction until #693"
        return row

    if value is None:
        return verdict("not_checkable", NOT_MEASURED)
    if ref is None:
        return verdict("not_checkable", "the twin holds no number for this quantity")
    if not ref["comparable"]:
        return verdict("not_checkable", "the twin's number is not the same measurand")
    if kind in EXACT:
        ok = value == twin
        return verdict("pass" if ok else "fail", "equal" if ok else "not equal")
    if kind not in SCALAR and kind not in ("point", "direction"):
        return verdict("not_checkable", f"no comparison rule for a {kind}")
    if thr is None:
        return verdict("not_checkable", "no acceptance threshold committed")
    if thr < 2 * unc:
        return verdict("not_checkable", "the threshold is less than twice the uncertainty")
    dev = deviation(kind, twin, value)
    row["deviation"] = round(dev, 6)
    return verdict("pass" if dev <= thr else "fail", f"deviation {'<=' if dev <= thr else '>'} threshold")


def check(contract: dict, hypotheses: dict, twin_dir: Path, contract_sha256: str | None = None,
          contract_path: str = "params/interface-contract.json") -> dict:
    params = Params(twin_dir)
    errors = validate(contract, hypotheses, params)
    if errors:
        raise ContractError("\n".join(errors))
    scale_open = any(p.get("id") == "#693-scale" and p.get("state") != "closed"
                     for p in contract.get("preconditions", []))
    rows, per_iface = [], {}
    for iface, q in quantities(contract):
        row = check_quantity(q, params, scale_open, iface["id"])
        rows.append(row)
        tally = per_iface.setdefault(iface["id"], {"pass": 0, "fail": 0, "not_checkable": 0})
        tally[row["status"]] += 1
    count = {s: sum(r["status"] == s for r in rows) for s in ("pass", "fail", "not_checkable")}
    reasons: dict[str, int] = {}
    for r in rows:
        if r["status"] == "not_checkable":
            reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    by_hyp: dict[str, dict] = {}
    for r in rows:
        if r["hypothesis"]:
            t = by_hyp.setdefault(r["hypothesis"], {"pass": 0, "fail": 0, "not_checkable": 0})
            t[r["status"]] += 1
    return {
        "schema": SCHEMA,
        "issue": contract.get("issue"),
        "contract": contract_path,
        "contract_id": contract.get("contract_id"),
        "contract_revision": contract.get("revision"),
        "contract_sha256": contract_sha256,
        "params_sha256": dict(sorted(params.hashes.items())),
        "checker": "source/check_interface_contract.py",
        "independence": "reads the contract and the twin's params JSON only and imports the standard library only; shares no code with the scripts that fitted the features or built the body",
        "claims": "a pass compares a twin number with an admitted value within a committed threshold; it is not a measurement and releases nothing. Today no value is filled, so every quantity is not checkable and nothing about the specimen is established.",
        "scale": "open: owner instruction, 1 scan unit = 1 mm (#693)" if scale_open else "calibrated (#693 closed)",
        "summary": {
            "interfaces": len(per_iface),
            "quantities": len(rows),
            "with_a_twin_number": sum(r["twin_number_not_evidence"] is not None for r in rows),
            **count,
            "not_checkable_reasons": dict(sorted(reasons.items())),
            "twin_numbers_changed_since_writing": [r["id"] for r in rows if r["twin_changed_since_writing"]],
            "by_interface": per_iface,
            "by_hypothesis": dict(sorted(by_hyp.items())),
        },
        "rows": rows,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--twin", type=Path, default=TWIN, help="twin directory (default: this script's twin)")
    ap.add_argument("--contract", type=Path, default=None, help="default: <twin>/params/interface-contract.json")
    ap.add_argument("--out", type=Path, default=None, help="default: <twin>/params/interface-contract-check.json")
    args = ap.parse_args(argv)
    contract_path = args.contract or args.twin / "params" / "interface-contract.json"
    out = args.out or args.twin / "params" / "interface-contract-check.json"
    data = contract_path.read_bytes()
    contract = json.loads(data)
    hypotheses = json.loads((args.twin / "hypotheses.json").read_text())
    try:
        rel = contract_path.resolve().relative_to(args.twin.resolve()).as_posix()
    except ValueError:
        rel = str(contract_path)
    try:
        record = check(contract, hypotheses, args.twin, sha256_bytes(data), rel)
    except ContractError as exc:
        print(f"contract refused, nothing written:\n{exc}", file=sys.stderr)
        return 2
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    s = record["summary"]
    print(f"{s['interfaces']} interfaces, {s['quantities']} quantities: {s['pass']} pass, {s['fail']} fail, "
          f"{s['not_checkable']} not checkable -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
