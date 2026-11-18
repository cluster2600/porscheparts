#!/usr/bin/env python3
"""Conversion chain and native floating-point bounds of the bionic turbo F1 (issue #397).

Primary reader and checker for gate G04-native-fp-execution. It applies the
prescription of conversion-contract.json: the stages exact rational -> 16-digit
text (S1), native read through binary128 (S2), native write at writePrecision 16
(S3) and reread (S4); the operation bounds of the native face, closure and guard
computations on frozen synthetic reference cells; the threshold conversions;
the certified margins read from pinned certificates. It uses hardware binary64
and exact `Fraction` arithmetic. It never runs OpenFOAM, Docker, a mesher, a
solver or a turbo case, and it selects no native input.

Commands, from the repository root:

    python3 twins/bionic-turbo-f1/fp-chain-20261118/fpchain.py check
    python3 twins/bionic-turbo-f1/fp-chain-20261118/fpchain.py apply --source-archive <OpenFOAM-v2406.tgz> --write
    python3 twins/bionic-turbo-f1/fp-chain-20261118/fpchain.py gate

`check` exits non-zero on any stale hash, changed receipt, failed bound or
ledger drift. `gate` prints the unchanged evaluator's verdict for G04.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import struct
import sys
import tarfile
from fractions import Fraction as Fr
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TWIN = "twins/bionic-turbo-f1"
REVISION = TWIN + "/fp-chain-20261118"
PARENT_LEDGER = TWIN + "/basis-20261112/gate-ledger.json"
MATRIX = TWIN + "/baseline-20261106-mac/runtime-matrix.json"
EVALUATOR = TWIN + "/baseline-20261106/baseline.py"
BASIS = TWIN + "/basis-20261112/basis.py"
GATE = "G04-native-fp-execution"
ROW = "opencfd-v2406-runtime"

FILES = {
    "contract": "conversion-contract.json",
    "readback": "runtime-readback-20261118.json",
    "conversions": "conversion-receipt.json",
    "independent": "independent-readback.json",
    "ledger": "gate-ledger.json",
    "attestation": "G04-attestation.json",
    "evaluation": "G04-evaluation.json",
    "prerequisites": "prerequisites.json",
    "host": "host-observations-20261118.json",
}
PROGRAMS = ("fpchain.py", "independent_reader.py", "readback_image.py")

U = Fr(1, 2 ** 53)
U128 = Fr(1, 2 ** 113)
EPS_DEC16 = Fr(1, 2 * 10 ** 15)
EPS_READ = U + Fr(1, 2 ** 111)
BETA = (1 + EPS_DEC16) * (1 + EPS_READ) - 1
KEPT_BLOCKERS_REQUIRED = {"pinned-binary-not-executed", "no-admissible-native-input",
                          "criterion-sensitivity-and-conditioning-not-certified",
                          "compiler-and-options-not-pinned"}


class ChainError(Exception):
    """Raised when a contract value or a witness is malformed."""


# --------------------------------------------------------------------------
# Files and the unchanged modules this revision relies on
# --------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def load(name: str, base: Path = HERE):
    return load_json(base / FILES[name])


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parent():
    """The unchanged baseline evaluator."""
    return _module("turbo_fp_parent_baseline", REPO / EVALUATOR)


def basis():
    """The unchanged G03 revision, for its prerequisite evaluation."""
    return _module("turbo_fp_basis", REPO / BASIS)


# --------------------------------------------------------------------------
# Exact binary and decimal rounding
# --------------------------------------------------------------------------

def floor_log2(a: Fr) -> int:
    e = a.numerator.bit_length() - a.denominator.bit_length()
    while Fr(2) ** e > a:
        e -= 1
    while Fr(2) ** (e + 1) <= a:
        e += 1
    return e


def floor_log10(a: Fr) -> int:
    e = len(str(a.numerator)) - len(str(a.denominator))
    while Fr(10) ** e > a:
        e -= 1
    while Fr(10) ** (e + 1) <= a:
        e += 1
    return e


def round_binary(q: Fr, precision: int, emin: int, emax: int) -> Fr:
    """Round to nearest, ties to even, in a binary format with subnormals."""
    if q == 0:
        return Fr(0)
    a = abs(q)
    quantum = max(floor_log2(a), emin) - precision + 1
    m = a / Fr(2) ** quantum
    n, r = divmod(m.numerator, m.denominator)
    if 2 * r > m.denominator or (2 * r == m.denominator and n & 1):
        n += 1
    result = n * Fr(2) ** quantum
    if result >= Fr(2) ** (emax + 1):
        raise OverflowError("overflow")
    return result if q > 0 else -result


def rn64(q: Fr) -> Fr:
    return round_binary(Fr(q), 53, -1022, 1023)


def rn128(q: Fr) -> Fr:
    return round_binary(Fr(q), 113, -16382, 16383)


def bits(x) -> str:
    return "0x%016x" % struct.unpack("<Q", struct.pack("<d", float(x)))[0]


def rational(text) -> Fr:
    """Exact value of a contract number: p/q, decimal, 2^k, p/10^k or binary64(literal)."""
    s = str(text).strip()
    if m := re.fullmatch(r"(-?)2\^(-?\d+)", s):
        return (-1 if m[1] else 1) * Fr(2) ** int(m[2])
    if m := re.fullmatch(r"binary64\((.+)\)", s):
        return rn64(Fr(m[1]))
    if m := re.fullmatch(r"(-?\d+)/10\^(\d+)", s):
        return Fr(int(m[1]), 10 ** int(m[2]))
    try:
        return Fr(s)
    except (ValueError, ZeroDivisionError) as error:
        raise ChainError(f"not an exact number: {text!r}") from error


VSMALL64 = rn64(Fr("1e-300"))
VGREAT64 = rn64(Fr("1e300"))
ROOTVSMALL64 = rn64(Fr("1e-150"))
CLOSED64 = rn64(Fr("1e-6"))


def gamma(k: int) -> Fr:
    if k * U >= 1:
        raise ChainError(f"gamma({k}) undefined")
    return k * U / (1 - k * U)


def dec16(q: Fr) -> tuple[str, bool]:
    """S1: correctly rounded 16 significant digits, ties to even, in %.16g style."""
    if q == 0:
        return "0", False
    a = abs(q)
    e = floor_log10(a)
    m = a * Fr(10) ** (15 - e)
    n, r = divmod(m.numerator, m.denominator)
    tie = 2 * r == m.denominator
    if 2 * r > m.denominator or (tie and n & 1):
        n += 1
    if n == 10 ** 16:
        n, e = 10 ** 15, e + 1
    return ("-" if q < 0 else "") + format_g(str(n), e), tie


def format_g(digits: str, e: int) -> str:
    if e < -4 or e >= 16:
        mantissa = digits[0] + ("." + digits[1:].rstrip("0") if digits[1:].rstrip("0") else "")
        return f"{mantissa}e{'-' if e < 0 else '+'}{abs(e):02d}"
    if e >= 0:
        whole, fraction = digits[:e + 1], digits[e + 1:].rstrip("0")
    else:
        whole, fraction = "0", ("0" * (-e - 1) + digits).rstrip("0")
    return whole + ("." + fraction if fraction else "")


def s3_write(x: float) -> str:
    """S3: the native writer at precision 16 (CPython's correctly rounded %.16g)."""
    text = "%.16g" % x
    if x != 0 and text != dec16(Fr(x))[0]:
        raise ChainError(f"two primary formatters disagree on {x!r}")
    return text


def lemma_applies(text: str) -> bool | None:
    """Double-rounding lemma: |D| < 10^16, last-digit exponent q >= -25, |T| < 2^113."""
    m = re.fullmatch(r"[-+]?(\d*)\.?(\d*)(?:[eE]([-+]?\d+))?", text)
    if not m or not (m[1] or m[2]):
        return None
    digits = (m[1] + m[2]).lstrip("0") or "0"
    q = int(m[3] or 0) - len(m[2])
    stripped = digits.rstrip("0")
    q += len(digits) - len(stripped)
    return len(stripped or "0") <= 16 and q >= -25 and abs(Fr(text)) < Fr(2) ** 113


def s2_read(text: str) -> dict:
    """S2: the native ASCII reader of OpenFOAM v2406, as prescribed from its source."""
    record = {"text": text if len(text) <= 64 else text[:20] + f"...({len(text)} characters)"}
    if len(text) >= 128:
        record.update(branch="length-refusal", x_bits=None)
        return record
    label_candidate = text[0] != "."
    for char in text[1:]:
        if label_candidate:
            label_candidate = char.isdigit()
    if label_candidate and text != "-":
        value = int(text)
        if -2 ** 31 <= value < 2 ** 31:
            x = float(value)
            record.update(branch="label", x_bits=bits(x), x=x)
            return record
        record["label_overflow"] = True
    exact = Fr(text)
    q = rn128(exact)
    record["q128"] = str(q)
    if -VSMALL64 <= q <= VSMALL64:
        record.update(branch="zero", x_bits=bits(0.0), x=0.0)
    elif q < -VGREAT64 or q > VGREAT64:
        record.update(branch="range-refusal", x_bits=None)
    else:
        x = float(rn64(q))
        correct = float(text)
        if Fr(correct) != rn64(exact):
            raise ChainError(f"two primary decimal readers disagree on {text!r}")
        record.update(branch="scalar", x_bits=bits(x), x=x, correct_rn64_bits=bits(correct),
                      double_rounding_discrepancy=x != correct, lemma=lemma_applies(text))
        if record["lemma"] and x != correct:
            raise ChainError(f"double-rounding lemma contradicted by {text!r}")
    return record


def read_error_ok(record: dict) -> bool:
    if record["branch"] == "scalar":
        return abs(Fr(record["x"]) - Fr(record["text"])) <= EPS_READ * abs(Fr(record["text"]))
    if record["branch"] == "zero":
        return abs(Fr(record["text"])) <= VSMALL64 * (1 + U128)
    return True


def strip(record: dict) -> dict:
    return {k: v for k, v in record.items() if k not in ("x",)}


def chain_rational(item: dict) -> dict:
    r = rational(item["value"])
    t1, tie = dec16(r)
    out = {"id": item["id"], "value": item["value"], "S1": t1, "S1_tie": tie}
    if r != 0:
        e = floor_log10(abs(r))
        out["S1_within_bound"] = abs(Fr(t1) - r) <= Fr(10) ** (e - 15) / 2 and abs(Fr(t1) - r) <= EPS_DEC16 * abs(r)
    else:
        out["S1_within_bound"] = t1 == "0"
    read1 = s2_read(t1)
    out["S2"] = strip(read1)
    out["S2_within_bound"] = read_error_ok(read1)
    if read1.get("x") is not None:
        x1 = read1["x"]
        if read1["branch"] in ("scalar", "label") and r != 0:
            out["chain_within_beta"] = abs(Fr(x1) - r) <= BETA * abs(r)
        t2 = s3_write(x1)
        out["S3"] = t2
        out["S3_within_bound"] = abs(Fr(t2) - Fr(x1)) <= EPS_DEC16 * abs(Fr(x1))
        read2 = s2_read(t2)
        out["S4"] = strip(read2)
        if read2.get("x") is not None:
            if read1["branch"] in ("scalar", "label") and read2["branch"] in ("scalar", "label") and r != 0:
                out["chain_within_budget_K1"] = abs(Fr(read2["x"]) - r) <= ((1 + BETA) ** 2 - 1) * abs(r)
            out["binary_text_binary_identity"] = read2["x_bits"] == read1["x_bits"]
        out["text_binary_text_identity"] = t2 == t1
    if r != 0 and rn64(r) == r and abs(r) <= VGREAT64:
        x = float(r)
        t = s3_write(x)
        back = s2_read(t)
        out["binary64_cycle"] = {"x_bits": bits(x), "S3": t, "S4": strip(back),
                                 "identity": back.get("x_bits") == bits(x)}
    return out


def chain_text(item: dict) -> dict:
    text = "1" * 128 if item["text"] == "repeat '1' 128 times" else item["text"]
    read1 = s2_read(text)
    out = {"id": item["id"], "S2": strip(read1), "S2_within_bound": read_error_ok(read1)}
    if read1.get("x") is not None:
        t2 = s3_write(read1["x"])
        read2 = s2_read(t2)
        out.update(S3=t2, S4=strip(read2), binary_text_binary_identity=read2.get("x_bits") == read1["x_bits"])
    if item["id"] == "text-minus-zero-label":
        out["S3_of_negative_zero"] = s3_write(-0.0)
    return out


def coverage(rationals: list, texts: list) -> dict:
    rows = {r["id"]: r for r in rationals}
    trows = {t["id"]: t for t in texts}
    reads = [(r["id"], r["S2"]) for r in rationals] + [(r["id"], r["S4"]) for r in rationals if "S4" in r] \
        + [(t["id"], t["S2"]) for t in texts] + [(t["id"], t["S4"]) for t in texts if "S4" in t] \
        + [(r["id"], r["binary64_cycle"]["S4"]) for r in rationals if "binary64_cycle" in r]

    def ids(predicate):
        return sorted({wid for wid, read in reads if predicate(read)})

    tiny = Fr(2) ** -1022
    cov = {
        "finite-normal": ids(lambda s: s["branch"] == "scalar" and abs(Fr(s.get("q128", "0"))) >= tiny),
        "certificate-rational": sorted(w for w in ("domain-lower", "domain-upper", "leaf-1930-lower") if w in rows),
        "subnormal": sorted(r["id"] for r in rationals if 0 < abs(rational(r["value"])) < tiny)
        + sorted(t["id"] for t in texts if t["S2"]["branch"] == "zero" and 0 < abs(Fr(t["S2"]["text"])) < tiny),
        "near-zero-below-vsmall": ids(lambda s: s["branch"] == "zero" and Fr(s["text"]) != 0),
        "vsmall-boundary": sorted(w for w in ("text-1e-300", "text-above-vsmall") if w in trows
                                  and trows[w]["S2"]["branch"] in ("zero", "scalar"))
        + (["vsmall64"] if rows.get("vsmall64", {}).get("binary64_cycle", {}).get("S4", {}).get("branch") == "zero" else []),
        "vgreat-boundary": sorted(w for w, b in (("text-1e300", "scalar"), ("text-above-vgreat", "range-refusal"))
                                  if trows.get(w, {}).get("S2", {}).get("branch") == b),
        "signed-zero": sorted(t["id"] for t in texts if t["S2"]["text"].startswith("-")
                              and t["S2"].get("x_bits") == bits(0.0)),
        "negative-values": sorted({r["id"] for r in rationals if rational(r["value"]) < 0}
                                  | {t["id"] for t in texts if t["S2"]["text"].startswith("-")}),
        "decimal16-tie": sorted(r["id"] for r in rationals if r["S1_tie"]),
        "label-token": ids(lambda s: s["branch"] == "label"),
        "label-overflow": ids(lambda s: s.get("label_overflow")),
        "roundtrip-binary-text-binary-fails": sorted(r["id"] for r in rationals
                                                     if r.get("binary64_cycle", {}).get("identity") is False),
        "roundtrip-text-binary-text-fails": sorted(r["id"] for r in rationals if r.get("text_binary_text_identity") is False),
        "double-rounding-discrepancy": ids(lambda s: s.get("double_rounding_discrepancy")),
        "token-length-limit": ids(lambda s: s["branch"] == "length-refusal"),
    }
    return cov


# --------------------------------------------------------------------------
# Thresholds and the libm bracket of the non-orthogonality cosine
# --------------------------------------------------------------------------

def cos_enclosure(x: Fr, bits_after: int = 220) -> tuple[Fr, Fr]:
    """Alternating Taylor series; consecutive partial sums enclose cos(x) for 0 < x < 2."""
    term, total, k = Fr(1), Fr(1), 0
    previous = None
    while True:
        k += 1
        term = -term * x * x / ((2 * k - 1) * (2 * k))
        previous, total = total, total + term
        if abs(term) < Fr(1, 2 ** bits_after):
            return (min(previous, total), max(previous, total))


def thresholds(contract: dict) -> dict:
    rows = []
    for item in contract["thresholds"]:
        if "literal" not in item:
            continue
        exact = Fr(item["literal"])
        value = rn64(exact)
        text = s3_write(float(value))
        back = s2_read(text)
        rows.append({"id": item["id"], "literal": item["literal"], "binary64": str(value), "bits": bits(value),
                     "relation_to_literal": "equal" if value == exact else ("above" if value > exact else "below"),
                     "S3": text, "S4_branch": back["branch"],
                     "survives_native_cycle": back.get("x_bits") == bits(value)})
    pi64 = Fr(math.pi)
    argument = (70.0 * math.pi) / 180.0
    if Fr(argument) != rn64(rn64(70 * pi64) / 180):
        raise ChainError("binary64 evaluation of degToRad(70) disagrees with its exact rounding")
    low, high = cos_enclosure(Fr(argument))
    exponent = floor_log2(low)
    quantum = Fr(2) ** (exponent - 52)
    down = (low // quantum) * quantum
    up = down + quantum
    if not (down < low and high < up):
        raise ChainError("the cosine enclosure straddles a binary64 value")
    midpoint = (down + up) / 2
    nearest = down if high < midpoint else (up if low > midpoint else None)
    distance = float((low - midpoint) / quantum)
    return {"literals": rows,
            "non_orthogonality_cosine": {
                "argument_bits": bits(argument), "pi64_bits": bits(math.pi),
                "exact_cosine_enclosure_width": "2^-220 or less",
                "exact_cosine_approx": "%.17e" % float(low),
                "neighbour_down_bits": bits(down), "neighbour_up_bits": bits(up),
                "round_to_nearest_bits": bits(nearest) if nearest is not None else None,
                "distance_from_midpoint_in_ulps": "%.6f" % distance,
                "bracket": [str(down), str(up)],
                "libm_result": "not observed; the pinned arm64 libm was not executed"}}


# --------------------------------------------------------------------------
# Certificates: retained boxes, recorded constants and margins
# --------------------------------------------------------------------------

def certificate(contract: dict, cid: str, repo: Path = REPO):
    item = next(c for c in contract["certificates"] if c["id"] == cid)
    path = repo / item["path"]
    actual = sha256_file(path)
    if actual != item["sha256"]:
        raise ChainError(f"certificate {cid} is stale: pinned {item['sha256']}, found {actual}")
    return load_json(path)


def certificates(contract: dict, cos_bracket: list, repo: Path = REPO) -> dict:
    dossier = certificate(contract, "dossier", repo)
    tets = certificate(contract, "face-tets-summary", repo)
    tets_rb = certificate(contract, "face-tets-readback", repo)
    flat = certificate(contract, "flatness-summary", repo)
    flat_rb = certificate(contract, "flatness-readback", repo)
    ortho = certificate(contract, "orthogonality-summary", repo)
    ortho_rb = certificate(contract, "orthogonality-readback", repo)
    skew = certificate(contract, "skewness-summary", repo)
    weight = certificate(contract, "weight-summary", repo)
    weight_rb = certificate(contract, "weight-readback", repo)
    ratio_rb = certificate(contract, "volume-ratio-readback", repo)
    kept = contract["retained"]
    leaves = [box["parent_leaf"] for box in tets["box_results"]]
    retained = {
        "dossier_domain_v": dossier["domain_v"], "dossier_source_boxes": dossier["source_boxes"],
        "contract_domain_v": kept["domain_v"],
        "boxes": len(leaves), "first_leaf": leaves[0], "last_leaf": leaves[-1],
        "leaves_contiguous": leaves == list(range(kept["leaves"][0], kept["leaves"][1] + 1)),
        "envelope_lower_equals_first_box": tets["box_results"][0]["lower"] == kept["domain_v"][0],
        "envelope_upper_equals_last_box": tets["box_results"][-1]["upper"] == kept["domain_v"][1],
        "all_153_closed_boxes_preserved": tets["all_153_closed_boxes_preserved"],
        "determinant_indecisions_1929_1930_unchanged": tets["determinant_indecisions_1929_1930_unchanged"],
        "undecided_determinant_leaves": kept["undecided_determinant_leaves"],
        "native_admission": dossier["native_admission"] or tets["native_admission"],
        "point_selected": False,
    }
    retained["all_kept"] = (retained["boxes"] == kept["boxes"] and retained["leaves_contiguous"]
                            and dossier["domain_v"] == kept["domain_v"] and dossier["source_boxes"] == kept["boxes"]
                            and retained["envelope_lower_equals_first_box"] and retained["envelope_upper_equals_last_box"]
                            and retained["all_153_closed_boxes_preserved"] is True
                            and retained["determinant_indecisions_1929_1930_unchanged"] is True
                            and not retained["native_admission"])
    leaf_1930 = next(b for b in tets["box_results"] if b["parent_leaf"] == 1930)
    witness = next(w for w in contract["witnesses"]["rationals"] if w["id"] == "leaf-1930-lower")
    retained["leaf_1930_lower_equals_witness"] = leaf_1930["lower"] == witness["value"]
    small64 = rn64(Fr("1e-15"))
    tol_low, tol_high = (Fr(v) for v in tets_rb["threshold_interval"])
    ortho_low, ortho_high = (Fr(v) for v in ortho_rb["threshold"])
    recorded = [
        ("flatness-readback.ROOTVSMALL", flat_rb["ROOTVSMALL"], "1e-150"),
        ("flatness-readback.VSMALL", flat_rb["VSMALL"], "1e-300"),
        ("flatness-readback.flatness_threshold", flat_rb["flatness_threshold"], "0.8"),
        ("orthogonality-readback.ROOTVSMALL", ortho_rb["ROOTVSMALL"], "1e-150"),
        ("weight-readback.threshold", weight_rb["threshold"], "0.05"),
        ("weight-readback.VSMALL", weight_rb["VSMALL"], "1e-300"),
        ("volume-ratio-readback.threshold", ratio_rb["threshold"], "0.01"),
        ("volume-ratio-readback.VSMALL", ratio_rb["VSMALL"], "1e-300"),
    ]
    constants = [{"certificate_value": name, "literal": literal, "equals_binary64_of_literal": Fr(value) == rn64(Fr(literal))}
                 for name, value, literal in recorded]
    down, up = (Fr(v) for v in cos_bracket)
    ulp = up - down
    intervals = {
        "sqr_SMALL_interval_contains_exact_square": tol_low <= small64 ** 2 <= tol_high,
        "sqr_SMALL_interval_contains_binary64_square": tol_low <= rn64(small64 ** 2) <= tol_high,
        "orthogonality_threshold_interval_contains_libm_bracket": ortho_low <= down and up <= ortho_high,
        "orthogonality_threshold_interval_upper_minus_bracket_down_in_ulps": "%.6f" % float((ortho_high - down) / ulp),
        "orthogonality_threshold_interval_note": "the 2026-10-13 interval encloses the mathematical cos(70 degrees); the native threshold is cos of the binary64 argument, whose two binary64 neighbours lie above that interval; margins below use the far end of the libm bracket",
    }
    w64, f64, r64 = rn64(Fr("0.05")), rn64(Fr("0.8")), rn64(Fr("0.01"))

    def margin(cid, certified, threshold, comparison, note):
        m = certified - threshold if comparison == "above" else threshold - certified
        return {"criterion": cid, "certified_bound": str(certified), "certified_approx": "%.12g" % float(certified),
                "threshold": str(threshold), "threshold_approx": "%.12g" % float(threshold),
                "margin": str(m), "margin_approx": "%.6e" % float(m),
                "margin_in_u_times_threshold": "%.4e" % float(m / (U * abs(threshold))),
                "certified_side": m > 0, "native_decision": "undecided: sensitivity and conditioning not certified",
                "note": note}

    margins = [
        margin("G6-flatness", Fr(flat["minimum_positive_record_bounds"]["flatness"]["lower"]), f64, "above",
               f"lowest certified flatness lower bound; {flat['counts']['unknown']} envelope records stay unknown and are covered by local records"),
        margin("G5-non-orthogonality", Fr(ortho["minimum_positive_certificate"]["lower"]), max(up, ortho_high), "above",
               f"measured against the far end of the libm bracket of the native threshold; {ortho['category_counts']['matrix:unknown']} matrix and {ortho['category_counts']['witness:unknown']} witness records stay unknown"),
        margin("G9-skewness", Fr(skew["maximum_positive_upper"]), Fr(4), "below",
               f"highest certified skewness upper bound; {skew['envelope_counts']['unknown']} envelope records covered locally"),
        margin("G7-weights", Fr(weight["minimum_positive_lower"]), w64, "above",
               f"lowest certified weight lower bound; {weight['envelope_counts']['unknown']} envelope records covered locally"),
        margin("G8-volume-ratio", Fr(ratio_rb["minimum_ratio_lower"]), r64, "above", "lowest certified volume-ratio lower bound"),
        margin("G1-face-guard", 2 * Fr(flat["minimum_positive_record_bounds"]["magS"]["lower"]), ROOTVSMALL64, "above",
               "twice the lowest certified |A_f|, a lower bound of the exact fan sum around any centre"),
    ]
    mags = Fr(flat["minimum_positive_record_bounds"]["magS"]["lower"])
    beta_k1 = (1 + BETA) ** 2 - 1
    denominator = 12 * beta_k1 * (2 + beta_k1) + 32 * gamma(4) * (2 + gamma(4))
    r2 = (2 * mags - ROOTVSMALL64 / (1 - gamma(6))) / denominator
    r_crit = Fr(math.isqrt(r2.numerator * 10 ** 12 // r2.denominator), 10 ** 6)
    guard = {
        "rule": "for quads with every |coordinate| <= R, the computed fan sum is at least (1 - gamma(6)) * (2|A_f| - 12 beta_K1 (2 + beta_K1) R^2 - 32 gamma(4) (2 + gamma(4)) R^2); the guard sumA < ROOTVSMALL is decided inactive for every quad when R <= R_crit",
        "magS_lower": str(mags), "beta_K1": "%.6e" % float(beta_k1),
        "R_crit_lower_bound": str(r_crit), "R_crit_approx": "%.6g" % float(r_crit),
        "R_crit_units": "the length unit of the written coordinates",
        "decided_here": False,
        "reason": "R_max of a written native input is read from that input; none exists",
        "scope_note": "magS bounds the exact PR236 native-centre representation on the 153 boxes; triangles have no guard",
    }
    return {"retained": retained, "recorded_constants": constants, "intervals": intervals,
            "margins": margins, "face_guard_critical_scale": guard,
            "files": {c["id"]: c["sha256"] for c in contract["certificates"]}}


# --------------------------------------------------------------------------
# Synthetic reference cells: exact, unfused and fused binary64
# --------------------------------------------------------------------------

def rotation(quaternion) -> list[list[Fr]]:
    a, b, c, d = (Fr(v) for v in quaternion)
    n = a * a + b * b + c * c + d * d
    return [[(a * a + b * b - c * c - d * d) / n, 2 * (b * c - a * d) / n, 2 * (b * d + a * c) / n],
            [2 * (b * c + a * d) / n, (a * a - b * b + c * c - d * d) / n, 2 * (c * d - a * b) / n],
            [2 * (b * d - a * c) / n, 2 * (c * d + a * b) / n, (a * a - b * b - c * c + d * d) / n]]


def native_point(exact: list[Fr]) -> tuple[float, float, float]:
    """S1 then S2 for each coordinate."""
    out = []
    for value in exact:
        read = s2_read(dec16(value)[0])
        if read.get("x") is None:
            raise ChainError(f"reference coordinate {value} is not readable")
        out.append(read["x"])
    return tuple(out)


def build_references(contract: dict) -> dict:
    spec = contract["reference_cells"]
    offset = [rational(v) for v in spec["offset"]]
    edge = rational(spec["edge"])
    rot = rotation(spec["rotation_quaternion"])

    def mapped(v, rotate, warp=None):
        vec = [Fr(c) for c in v]
        if warp:
            vec = [vec[i] + warp[i] for i in range(3)]
        if rotate:
            vec = [sum(rot[i][j] * vec[j] for j in range(3)) for i in range(3)]
        return [offset[i] + edge * vec[i] for i in range(3)]

    cells = []
    for item in spec["cells"]:
        hexa = item["shape"] == "hex"
        unit = spec["hex_unit_vertices"] if hexa else spec["prism_unit_vertices"]
        faces = spec["hex_faces"] if hexa else spec["prism_faces"]
        rotate = "R v" in item["map"]
        points = []
        for index, v in enumerate(unit):
            warp = [Fr(0), Fr(0), Fr(1, 10)] if item["id"].startswith("RC3") and index == 6 else None
            points.append(native_point(mapped(v, rotate, warp)))
        cells.append({"id": item["id"], "points": points, "faces": [list(f) for f in faces]})
    lattice = {}
    for k in range(3):
        for j in range(3):
            for i in range(3):
                lattice[(i, j, k)] = len(lattice)
    block_points = [None] * 27
    for (i, j, k), index in lattice.items():
        block_points[index] = native_point(mapped((i, j, k), True))
    block_faces, owner, neighbour, seen = [], [], [], {}
    block_cells = []
    for k in range(2):
        for j in range(2):
            for i in range(2):
                cell = len(block_cells)
                corners = [lattice[(i + dx, j + dy, k + dz)] for dx, dy, dz in spec["hex_unit_vertices"]]
                block_cells.append(corners)
                for local in spec["hex_faces"]:
                    face = [corners[v] for v in local]
                    key = frozenset(face)
                    if key in seen:
                        neighbour[seen[key]] = cell
                    else:
                        seen[key] = len(block_faces)
                        block_faces.append(face)
                        owner.append(cell)
                        neighbour.append(None)
    internal = [f for f in range(len(block_faces)) if neighbour[f] is not None]
    boundary = [f for f in range(len(block_faces)) if neighbour[f] is None]
    order = internal + boundary
    block = {"id": spec["block"]["id"], "points": block_points,
             "faces": [block_faces[f] for f in order], "owner": [owner[f] for f in order],
             "neighbour": [neighbour[f] for f in internal], "cells": len(block_cells)}
    guards = []
    for item in spec["guard_faces"]:
        s = rational(item["square_side"])
        square = [[0, 0, 0], [s, 0, 0], [s, s, 0], [0, s, 0]]
        guards.append({"id": item["id"], "points": [native_point([Fr(c) for c in p]) for p in square],
                       "faces": [[0, 1, 2, 3]]})
    return {"cells": cells, "block": block, "guards": guards}


def fma(a: float, b: float, c: float) -> float:
    """Fused multiply-add with one rounding; an exact zero takes the IEEE 754 sign rule."""
    exact = Fr(a) * Fr(b) + Fr(c)
    if exact == 0:
        product_negative = math.copysign(1.0, a) * math.copysign(1.0, b) < 0
        both_negative_zeros = a * b == 0 and c == 0 and product_negative and math.copysign(1.0, c) < 0
        return -0.0 if both_negative_zeros else 0.0
    return float(rn64(exact))


PAIRS = ((1, 2), (2, 0), (0, 1))


def cross(a, b, pattern: str):
    out = []
    for k1, k2 in PAIRS:
        if pattern in ("F1", "F3"):
            out.append(fma(a[k1], b[k2], -(a[k2] * b[k1])))
        elif pattern == "F2":
            out.append(fma(-a[k2], b[k1], a[k1] * b[k2]))
        else:
            out.append(a[k1] * b[k2] - a[k2] * b[k1])
    return out


def mag(v, pattern: str) -> float:
    if pattern == "F3":
        return math.sqrt(fma(v[0], v[0], fma(v[1], v[1], v[2] * v[2])))
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def face_area(points, face, pattern):
    p = [points[i] for i in face]
    n = len(p)
    if n == 3:
        e1 = [p[1][k] - p[0][k] for k in range(3)]
        e2 = [p[2][k] - p[0][k] for k in range(3)]
        return [0.5 * c for c in cross(e1, e2, pattern)], None, None
    centre = list(p[0])
    for i in range(1, n):
        centre = [centre[k] + p[i][k] for k in range(3)]
    centre = [c / n for c in centre]
    sum_n, sum_a = [0.0, 0.0, 0.0], 0.0
    for i in range(n):
        this, nxt = p[i], p[(i + 1) % n]
        a = [nxt[k] - this[k] for k in range(3)]
        b = [centre[k] - this[k] for k in range(3)]
        nv = cross(a, b, pattern)
        sum_n = [sum_n[k] + nv[k] for k in range(3)]
        sum_a = sum_a + mag(nv, pattern)
    return [0.5 * s for s in sum_n], centre, sum_a


def exact_area(points, face) -> list[Fr]:
    p = [[Fr(c) for c in points[i]] for i in face]
    total = [Fr(0)] * 3
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        for k, (k1, k2) in enumerate(PAIRS):
            total[k] += a[k1] * b[k2] - a[k2] * b[k1]
    return [t / 2 for t in total]


def canonical(values) -> str:
    return hashlib.sha256(",".join(str(Fr(v)) for v in values).encode()).hexdigest()


def sqrt_bounds(q: Fr, extra: int = 128) -> tuple[Fr, Fr]:
    if q == 0:
        return Fr(0), Fr(0)
    root = math.isqrt(q.numerator * q.denominator * 4 ** extra)
    scale = q.denominator * 2 ** extra
    return Fr(root, scale), Fr(root + 1, scale)


def face_bound(points, face, centre) -> tuple[list[Fr], list[list[Fr]], list[Fr]]:
    """Per-component bound, the per-triangle product sums and exact cross products."""
    p = [[Fr(c) for c in points[i]] for i in face]
    n = len(p)
    if n == 3:
        e1 = [p[1][k] - p[0][k] for k in range(3)]
        e2 = [p[2][k] - p[0][k] for k in range(3)]
        prod = [abs(e1[k1] * e2[k2]) + abs(e1[k2] * e2[k1]) for k1, k2 in PAIRS]
        return [gamma(4) / 2 * x for x in prod], [prod], []
    c = [Fr(v) for v in centre]
    per_triangle, crosses = [], []
    for i in range(n):
        a = [p[(i + 1) % n][k] - p[i][k] for k in range(3)]
        b = [c[k] - p[i][k] for k in range(3)]
        per_triangle.append([abs(a[k1] * b[k2]) + abs(a[k2] * b[k1]) for k1, k2 in PAIRS])
        crosses.append([a[k1] * b[k2] - a[k2] * b[k1] for k1, k2 in PAIRS])
    totals = [sum(t[k] for t in per_triangle) for k in range(3)]
    return [gamma(n + 3) / 2 * x for x in totals], per_triangle, crosses


PATTERNS = ("F0", "F1", "F2", "F3")


def evaluate_faces(points, faces) -> list[dict]:
    rows = []
    for face in faces:
        exact = exact_area(points, face)
        row = {"points": len(face), "exact_sha256": canonical(exact), "patterns": {}}
        areas = {}
        for pattern in PATTERNS:
            area, centre, sum_a = face_area(points, face, pattern)
            bound, products, crosses = face_bound(points, face, centre)
            errors = [abs(Fr(area[k]) - exact[k]) for k in range(3)]
            ok = all(errors[k] <= bound[k] for k in range(3))
            ratio = max((float(errors[k] / bound[k]) if bound[k] else 0.0) for k in range(3))
            entry = {"A_bits": [bits(v) for v in area], "within_bound": ok, "max_error_over_bound": "%.3e" % ratio}
            if sum_a is not None:
                n = len(face)
                low = sum(max(Fr(0), sqrt_bounds(sum(c * c for c in cr))[0] - gamma(4) * sqrt_bounds(sum(x * x for x in pr))[1])
                          for cr, pr in zip(crosses, products))
                high = sum(sqrt_bounds(sum(c * c for c in cr))[1] + gamma(4) * sqrt_bounds(sum(x * x for x in pr))[1]
                           for cr, pr in zip(crosses, products))
                lower, upper = (1 - gamma(n + 2)) * low, (1 + gamma(n + 2)) * high
                entry["sumA_bits"] = bits(sum_a)
                entry["sumA_in_interval"] = lower <= Fr(sum_a) <= upper
                entry["guard_computed_active"] = Fr(sum_a) < ROOTVSMALL64
                entry["guard_decision"] = ("inactive" if lower >= ROOTVSMALL64 else
                                           "active" if upper < ROOTVSMALL64 else "undecided")
                entry["guard_interval_approx"] = ["%.17e" % float(lower), "%.17e" % float(upper)]
            row["patterns"][pattern] = entry
            areas[pattern] = (area, bound)
        row["_areas"] = areas
        row["_exact"] = exact
        rows.append(row)
    return rows


def cell_closedness(face_rows, cell_faces, pattern) -> dict:
    """cell_faces: list of (face index, sign) in the source accumulation order."""
    s, d = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for index, sign in cell_faces:
        area = face_rows[index]["_areas"][pattern][0]
        s = [s[k] + area[k] if sign > 0 else s[k] - area[k] for k in range(3)]
        d = [d[k] + abs(area[k]) for k in range(3)]
    m = len(cell_faces)
    openness = max(abs(s[k]) / (d[k] + float(ROOTVSMALL64)) for k in range(3))
    upper, holds = Fr(0), True
    for k in range(3):
        abs_sum = sum(abs(Fr(face_rows[i]["_areas"][pattern][0][k])) for i, _ in cell_faces)
        b = sum(face_rows[i]["_areas"][pattern][1][k] for i, _ in cell_faces) + gamma(m - 1) * abs_sum
        holds = holds and abs(Fr(s[k])) <= b
        upper = max(upper, (1 + U) ** 2 * b / ((1 - gamma(m - 1)) * abs_sum + ROOTVSMALL64) / (1 - U))
    exact_zero = all(sum(sign * face_rows[i]["_exact"][k] for i, sign in cell_faces) == 0 for k in range(3))
    return {"S_bits": [bits(v) for v in s], "S_is_floating_zero": all(v == 0.0 for v in s),
            "exact_sum_is_zero": exact_zero, "S_within_bound": holds,
            "openness_bits": bits(openness), "openness_upper_approx": "%.3e" % float(upper),
            "openness_within_upper": Fr(openness) <= upper,
            "decision": "closed" if upper <= CLOSED64 else "undecided",
            "computed_flagged_open": Fr(openness) > CLOSED64}


def boundary_closedness(face_rows, boundary, pattern) -> dict:
    s, total = [0.0, 0.0, 0.0], 0.0
    for index in boundary:
        area = face_rows[index]["_areas"][pattern][0]
        s = [s[k] + area[k] for k in range(3)]
        total = total + mag(area, pattern)
    openness = [s[k] / (total + float(VSMALL64)) for k in range(3)]
    nb = len(boundary)
    norms = sum(sqrt_bounds(sum(Fr(c) ** 2 for c in face_rows[i]["_areas"][pattern][0]))[0] for i in boundary)
    denominator = (1 - gamma(nb - 1)) * (1 - gamma(3)) * norms + VSMALL64
    upper, holds = Fr(0), True
    for k in range(3):
        abs_sum = sum(abs(Fr(face_rows[i]["_areas"][pattern][0][k])) for i in boundary)
        b = sum(face_rows[i]["_areas"][pattern][1][k] for i in boundary) + gamma(nb - 1) * abs_sum
        holds = holds and abs(Fr(s[k])) <= b
        upper = max(upper, (1 + U) ** 2 / (1 - U) * b / denominator)
    exact_zero = all(sum(face_rows[i]["_exact"][k] for i in boundary) == 0 for k in range(3))
    computed = max(abs(v) for v in openness)
    return {"faces": nb, "S_bits": [bits(v) for v in s], "S_is_floating_zero": all(v == 0.0 for v in s),
            "exact_sum_is_zero": exact_zero, "S_within_bound": holds,
            "openness_max_bits": bits(computed), "openness_upper_approx": "%.3e" % float(upper),
            "openness_within_upper": Fr(computed) <= upper,
            "decision": "closed" if upper <= CLOSED64 else "undecided",
            "computed_flagged_open": Fr(computed) > CLOSED64}


def references(contract: dict) -> dict:
    refs = build_references(contract)
    out = {"cells": [], "block": None, "guards": []}
    for cell in refs["cells"]:
        rows = evaluate_faces(cell["points"], cell["faces"])
        order = [(i, 1) for i in range(len(rows))]
        out["cells"].append({
            "id": cell["id"], "points_bits": [[bits(c) for c in p] for p in cell["points"]],
            "faces": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
            "closedness": {p: cell_closedness(rows, order, p) for p in PATTERNS},
            "boundary": {p: boundary_closedness(rows, list(range(len(rows))), p) for p in PATTERNS}})
    block = refs["block"]
    rows = evaluate_faces(block["points"], block["faces"])
    n_internal = len(block["neighbour"])
    per_cell = {c: [] for c in range(block["cells"])}
    for f, cell in enumerate(block["owner"]):
        per_cell[cell].append((f, 1))
    for f, cell in enumerate(block["neighbour"]):
        per_cell[cell].append((f, -1))
    out["block"] = {
        "id": block["id"], "cells": block["cells"], "internal_faces": n_internal,
        "boundary_faces": len(block["faces"]) - n_internal,
        "points_sha256": hashlib.sha256("".join(bits(c) for p in block["points"] for c in p).encode()).hexdigest(),
        "faces": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows],
        "closedness": {str(c): {p: cell_closedness(rows, per_cell[c], p) for p in PATTERNS} for c in per_cell},
        "boundary": {p: boundary_closedness(rows, list(range(n_internal, len(rows))), p) for p in PATTERNS}}
    for guard in refs["guards"]:
        rows = evaluate_faces(guard["points"], guard["faces"])
        out["guards"].append({"id": guard["id"], "points_bits": [[bits(c) for c in p] for p in guard["points"]],
                              "face": {k: v for k, v in rows[0].items() if not k.startswith("_")}})
    return out


def reference_summary(refs: dict) -> dict:
    faces = [f for c in refs["cells"] for f in c["faces"]] + refs["block"]["faces"] + [g["face"] for g in refs["guards"]]
    patterns = [e for f in faces for e in f["patterns"].values()]
    closures = [v for c in refs["cells"] for v in c["closedness"].values()] + \
        [v for c in refs["block"]["closedness"].values() for v in c.values()]
    boundaries = [v for c in refs["cells"] for v in c["boundary"].values()] + list(refs["block"]["boundary"].values())
    guards = {g["id"]: sorted({e["guard_decision"] for e in g["face"]["patterns"].values()}) for g in refs["guards"]}
    return {
        "faces": len(faces), "face_pattern_evaluations": len(patterns),
        "all_within_bound": all(e["within_bound"] for e in patterns),
        "fused_differs_from_unfused": sum(1 for f in faces for p in PATTERNS[1:]
                                          if f["patterns"][p]["A_bits"] != f["patterns"]["F0"]["A_bits"]),
        "cell_closure_evaluations": len(closures),
        "cell_closures_exact_zero": all(c["exact_sum_is_zero"] for c in closures),
        "cell_closures_floating_nonzero": sum(1 for c in closures if not c["S_is_floating_zero"]),
        "cell_closures_within_bound": all(c["S_within_bound"] and c["openness_within_upper"] for c in closures),
        "cell_closure_decisions": sorted({c["decision"] for c in closures}),
        "boundary_evaluations": len(boundaries),
        "boundary_floating_nonzero": sum(1 for b in boundaries if not b["S_is_floating_zero"]),
        "boundary_within_bound": all(b["S_within_bound"] and b["openness_within_upper"] and b["exact_sum_is_zero"]
                                     for b in boundaries),
        "guard_decisions": guards,
        "guards_consistent": all(e["sumA_in_interval"] for g in refs["guards"] for e in g["face"]["patterns"].values()),
    }


# --------------------------------------------------------------------------
# Source facts (needs the private archive) and the receipt
# --------------------------------------------------------------------------

def source_facts(contract: dict, archive: Path) -> dict:
    archive_sha = sha256_file(archive)
    facts, hits = [], []
    with tarfile.open(archive) as tar:
        for fact in contract["source_archive"]["facts"]:
            data = tar.extractfile("OpenFOAM-v2406/" + fact["member"]).read()
            lines = data.decode("utf-8", "replace").split("\n")
            line = lines[fact["line"] - 1] if fact["line"] <= len(lines) else ""
            facts.append({"id": fact["id"], "member_sha256": hashlib.sha256(data).hexdigest(),
                          "literal_on_line": fact["literal"] in line})
        pattern = re.compile(rb"\b(fesetround|fesetenv|fesetexceptflag|feupdateenv|_FPU_SETCW)\b")
        scanned = 0
        for member in tar.getmembers():
            name = member.name
            if not member.isfile() or not re.match(r"OpenFOAM-v2406/(src|applications)/", name):
                continue
            if not name.endswith((".C", ".H", ".c", ".h")):
                continue
            scanned += 1
            data = tar.extractfile(member).read()
            for number, text in enumerate(data.split(b"\n"), 1):
                if pattern.search(text):
                    hits.append({"path": name.split("/", 1)[1], "line": number,
                                 "text": text.decode("utf-8", "replace").strip()[:120]})
    return {"archive_sha256": archive_sha, "archive_matches_contract": archive_sha == contract["source_archive"]["sha256"],
            "facts": facts, "all_facts_found": all(f["literal_on_line"] for f in facts),
            "rounding_mode_scan": {"files_scanned": scanned, "hits": hits}}


def compute(contract: dict, repo: Path = REPO) -> dict:
    rationals = [chain_rational(item) for item in contract["witnesses"]["rationals"]]
    texts = [chain_text(item) for item in contract["witnesses"]["texts"]]
    cov = coverage(rationals, texts)
    thr = thresholds(contract)
    certs = certificates(contract, thr["non_orthogonality_cosine"]["bracket"], repo)
    refs = references(contract)
    summary = reference_summary(refs)
    bound_flags = [v for r in rationals for k, v in r.items() if k.endswith("within_bound") or k.startswith("chain_within")] + \
        [t["S2_within_bound"] for t in texts]
    decisions = {"active", "inactive", "undecided"}
    acceptance = {
        "conversions_within_bounds": all(bound_flags),
        "every_witness_class_covered": all(cov.get(c) for c in contract["witness_classes"]),
        "operations_within_bounds": summary["all_within_bound"] and summary["cell_closures_within_bound"]
        and summary["boundary_within_bound"] and summary["guards_consistent"],
        "branches_classified": all(set(v) <= decisions for v in summary["guard_decisions"].values())
        and set(summary["cell_closure_decisions"]) <= {"closed", "undecided"},
        "certificates_pinned_and_retained": certs["retained"]["all_kept"] and certs["retained"]["leaf_1930_lower_equals_witness"],
    }
    findings = {
        "certificate_constants_equal_binary64": all(c["equals_binary64_of_literal"] for c in certs["recorded_constants"]),
        "certificate_intervals": certs["intervals"],
        "vsmall64_survives_native_cycle": next(t for t in thr["literals"] if t["id"] == "VSMALL")["survives_native_cycle"],
        "double_rounding_witnesses": cov["double-rounding-discrepancy"],
    }
    return {
        "schema": "bionic-turbo-fp-chain-receipt/v1",
        "issue": 397,
        "scope": "provisional synthetic; no physical turbo, no native input, no execution",
        "contract": {"path": REVISION + "/" + FILES["contract"], "sha256": sha256_file(HERE / FILES["contract"])},
        "constants": {"u": str(U), "eps_decimal16": str(EPS_DEC16), "eps_native_read": str(EPS_READ),
                      "beta_approx": "%.6e" % float(BETA), "budget_K1_approx": "%.6e" % float((1 + BETA) ** 2 - 1),
                      "VSMALL64_bits": bits(VSMALL64), "VGREAT64_bits": bits(VGREAT64),
                      "ROOTVSMALL64_bits": bits(ROOTVSMALL64), "closedThreshold64_bits": bits(CLOSED64)},
        "witnesses": {"rationals": rationals, "texts": texts},
        "coverage": cov,
        "thresholds": thr,
        "certificates": certs,
        "references": refs,
        "reference_summary": summary,
        "findings": findings,
        "acceptance": acceptance,
        "status": "passed" if all(acceptance.values()) else "failed",
    }


def apply(archive: Path, repo: Path = REPO) -> dict:
    contract = load("contract")
    receipt = compute(contract, repo)
    facts = source_facts(contract, archive)
    receipt["source_facts"] = facts
    receipt["acceptance"]["source_facts_found"] = facts["all_facts_found"] and facts["archive_matches_contract"]
    receipt["status"] = "passed" if all(receipt["acceptance"].values()) else "failed"
    return receipt


# --------------------------------------------------------------------------
# Runtime readback, attestation, ledger and gate
# --------------------------------------------------------------------------

def check_readback(readback: dict, contract: dict, repo: Path = REPO) -> list[str]:
    errors = []
    matrix = load_json(repo / MATRIX)
    row = next(r for r in matrix["rows"] if r["id"] == ROW)
    if readback.get("contract", {}).get("sha256") != sha256_file(HERE / FILES["contract"]):
        errors.append("readback: recorded contract hash differs from the contract")
    if "sha256:" + row["identity"]["image"].split("@sha256:")[1] != readback["oci"]["manifest_digest"]:
        errors.append("readback: manifest digest differs from the pinned identity.image")
    if (readback["config"]["os"], readback["config"]["architecture"]) != ("linux", "arm64"):
        errors.append("readback: image platform is not linux/arm64")
    for name, pinned in row["executables"].items():
        observed = readback["pinned_executables"].get(name, {}).get("observed")
        if observed != pinned:
            errors.append(f"readback: executable {name} observed {observed}, pinned {pinned}")
    if readback["checkMesh"]["sha256"] != row["executables"]["checkMesh"]:
        errors.append("readback: checkMesh ELF hash differs from the pin")
    if not readback.get("all_checks_passed") or not all(readback["checks"].values()):
        errors.append("readback: a static check failed")
    expected = {c["id"] for c in contract["runtime_target"]["static_checks"]} - {
        "compiler-string", "fused-multiply-add", "fast-math-marker", "runtime-libraries"}
    if expected - set(readback["checks"]):
        errors.append(f"readback: static checks missing {sorted(expected - set(readback['checks']))}")
    return errors


def runtime_observation(readback: dict, repo: Path = REPO) -> dict:
    matrix = load_json(repo / MATRIX)
    row = next(r for r in matrix["rows"] if r["id"] == ROW)
    image = readback["reference"] if readback["oci"]["manifest_digest"] in readback["reference"] else None
    official = load_json(repo / TWIN / "evidence/airflow-native-binary-20261012/source-receipt.json")
    api = official["selected_files"]["OpenFOAM-v2406/META-INFO/api-info"]["sha256"]
    version_seen = (readback["meta_info"]["api_info_sha256"] == api
                    and readback["libOpenFOAM"]["strings"]["_be01ca78-20240625"])
    return {"variant": row["variant"] if readback["checks"]["meta-info-manifest"] else None,
            "version": row["version"] if version_seen else None,
            "platform": "{os}/{architecture}".format(**readback["config"]),
            "identity": {"image": image},
            "executables": {"checkMesh": readback["checkMesh"]["sha256"]}}


def check_gate_ledger(ledger: dict, repo: Path = REPO) -> list[str]:
    base = parent()
    matrix = load_json(repo / MATRIX)
    previous = load_json(repo / PARENT_LEDGER)
    errors = base.check_ledger(ledger, matrix, repo)
    if ledger.get("parent_ledger") != PARENT_LEDGER or ledger.get("parent_ledger_sha256") != sha256_file(repo / PARENT_LEDGER):
        errors.append("gate ledger does not pin its parent ledger")
    for key in ("schema", "roadmap", "states", "opening_rule", "release_separation", "paired_comparison_contract"):
        if ledger.get(key) != previous.get(key):
            errors.append(f"gate ledger changed {key}; the opening rule and the contract are inherited")
    if [g["id"] for g in ledger.get("gates", [])] != [g["id"] for g in previous["gates"]]:
        errors.append("gate ledger changed the gate list")
        return errors
    for old, new in zip(previous["gates"], ledger["gates"]):
        if old["id"] != GATE and old != new:
            errors.append(f"gate {old['id']} changed; this revision only records G04")
    gate = next(g for g in ledger["gates"] if g["id"] == GATE)
    old = next(g for g in previous["gates"] if g["id"] == GATE)
    if gate.get("state") not in {"investigated", "blocked"}:
        errors.append(f"G04 state {gate.get('state')!r}: an investigation records blockers, it cannot pass the gate")
    for key in ("kind", "prerequisites", "issue", "title", "required_bindings"):
        if gate.get(key) != old.get(key):
            errors.append(f"G04 changed {key}")
    kept = {b["id"] for b in gate.get("blockers", [])}
    resolved = {b["id"] for b in gate.get("resolved_blockers", [])}
    for blocker in old.get("blockers", []):
        if blocker["id"] not in kept | resolved:
            errors.append(f"G04 dropped the inherited blocker {blocker['id']} without recording its resolution")
    for item in gate.get("resolved_blockers", []):
        if not item.get("receipts"):
            errors.append(f"G04 resolved blocker {item['id']} without receipts")
    if KEPT_BLOCKERS_REQUIRED - kept:
        errors.append(f"G04 lost blockers {sorted(KEPT_BLOCKERS_REQUIRED - kept)}")
    return errors


def evaluate_gate(base: Path = HERE, repo: Path = REPO) -> dict:
    accepted, reasons = parent().evaluate_gate(GATE, load("ledger", base), load_json(repo / MATRIX),
                                               load("attestation", base), repo)
    return {"gate": GATE, "may_open": accepted, "reasons": reasons,
            "ledger_sha256": sha256_file(base / FILES["ledger"]),
            "attestation_sha256": sha256_file(base / FILES["attestation"]),
            "evaluator": EVALUATOR, "evaluator_sha256": sha256_file(repo / EVALUATOR)}


def check_attestation(attestation: dict, readback: dict, ledger: dict, repo: Path = REPO) -> list[str]:
    errors = []
    observed = attestation.get("runtime", {}).get(ROW)
    if observed != runtime_observation(readback, repo):
        errors.append("attestation: runtime row differs from what the static readback observed")
    gate = next(g for g in ledger["gates"] if g["id"] == GATE)
    pins = {p["path"]: p["sha256"] for p in gate["config_pins"]}
    if attestation.get("config_sha256") != pins:
        errors.append("attestation: configuration hashes differ from the G04 pins")
    for program in PROGRAMS + (FILES["contract"],):
        if REVISION + "/" + program not in pins:
            errors.append(f"G04 does not pin {program}")
    if "nothing" not in attestation.get("execution_host", "").lower():
        errors.append("attestation: execution host must state that nothing was executed")
    return errors


def check_all(base: Path = HERE, repo: Path = REPO) -> list[str]:
    errors = []
    contract = load("contract", base)
    for key in ("stages", "operation_bounds", "branch_rule", "margin_rule", "admissibility_argument",
                "acceptance", "resource_limits", "witnesses", "reference_cells"):
        if key not in contract:
            errors.append(f"contract lacks {key}")
    if contract.get("prescribed_before_application") is not True or contract.get("physical_turbo_claim") is not False:
        errors.append("contract must be prescribed before application and claim no physical turbo")
    if set(contract.get("inherited_prohibitions", [])) != parent().REQUIRED_PROHIBITIONS:
        errors.append("contract does not inherit every baseline prohibition")
    readback = load("readback", base)
    errors += check_readback(readback, contract, repo)
    recorded = load("conversions", base)
    fresh = compute(contract, repo)
    for key in fresh:
        if key != "acceptance" and fresh[key] != recorded.get(key) and key != "status":
            errors.append(f"conversion receipt is stale: {key}")
    for key, value in fresh["acceptance"].items():
        if recorded["acceptance"].get(key) != value or not value:
            errors.append(f"conversion acceptance {key} failed or differs")
    facts = recorded.get("source_facts", {})
    if not (facts.get("all_facts_found") and facts.get("archive_matches_contract")
            and [f["id"] for f in facts.get("facts", [])] == [f["id"] for f in contract["source_archive"]["facts"]]):
        errors.append("conversion receipt: source facts missing or not found")
    if recorded.get("status") != "passed":
        errors.append("conversion receipt status is not passed")
    independent = load("independent", base)
    if independent.get("primary_receipt_sha256") != sha256_file(base / FILES["conversions"]):
        errors.append("independent readback does not read the current primary receipt")
    if independent.get("status") != "passed" or independent.get("mismatches"):
        errors.append("independent readback did not confirm the primary receipt")
    if independent.get("imports_primary") is not False:
        errors.append("independent reader must not import the primary")
    prerequisites = load("prerequisites", base)
    current = basis().verify_prerequisites(repo)
    for key, value in current.items():
        if prerequisites.get(key) != value:
            errors.append(f"prerequisites: recorded {key} differs from the current evaluation")
    if prerequisites.get("downstream_geometry_solver_and_release_authorized") is not False:
        errors.append("prerequisites: downstream execution must stay unauthorised")
    ledger = load("ledger", base)
    errors += check_gate_ledger(ledger, repo)
    errors += check_attestation(load("attestation", base), readback, ledger, repo)
    if evaluate_gate(base, repo) != load("evaluation", base):
        errors.append("recorded G04 evaluation differs from the unchanged evaluator's verdict")
    host = load("host", base)
    if not host.get("skipped_steps") or host.get("containers_created") != 0 or host.get("processes_from_image_executed") != 0:
        errors.append("host observations must state the skipped steps and that nothing ran from the image")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="verify the committed revision (default)")
    run = sub.add_parser("apply", help="apply the contract and write the primary receipt")
    run.add_argument("--source-archive", type=Path, required=True)
    run.add_argument("--write", action="store_true")
    sub.add_parser("gate", help="print the unchanged evaluator's verdict for G04")
    args = parser.parse_args(argv)
    command = args.command or "check"
    if command == "check":
        errors = check_all()
        for error in errors:
            print(f"ERROR {error}", file=sys.stderr)
        print("bionic turbo fp chain 2026-11-18: " + ("FAILED" if errors else "OK"))
        return 1 if errors else 0
    if command == "apply":
        receipt = apply(args.source_archive)
        text = dump_json(receipt)
        if args.write:
            (HERE / FILES["conversions"]).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        print(f"primary receipt: {receipt['status']}", file=sys.stderr)
        return 0 if receipt["status"] == "passed" else 1
    verdict = evaluate_gate()
    for reason in verdict["reasons"]:
        print(f"REFUSED {reason}")
    print(f"gate {GATE}: " + ("may open" if verdict["may_open"] else "stays closed"))
    return 0 if verdict["may_open"] else 1


if __name__ == "__main__":
    sys.exit(main())
