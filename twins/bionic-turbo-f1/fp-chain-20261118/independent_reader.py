#!/usr/bin/env python3
"""Independent reader of the G04 conversion receipt (issue #397).

It does not import fpchain.py. It re-derives every conversion stage, every
binary64 result of the synthetic reference cells and every certified margin
from the contract and the pinned certificate files, then compares them with
the primary receipt field by field. Its methods differ from the primary's:

- binary64 and binary128 values are produced by an integer-only IEEE 754
  emulation with signed zeros (no hardware floating point, no float());
- decimal text is produced and parsed by integer digit arithmetic (no %g,
  no strtod);
- the cosine threshold is enclosed with the decimal module at 120 digits.

    python3 twins/bionic-turbo-f1/fp-chain-20261118/independent_reader.py --write
    python3 twins/bionic-turbo-f1/fp-chain-20261118/independent_reader.py \
        --private-extract <dir of the static readback> --write
"""
from __future__ import annotations

import argparse
import decimal
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CONTRACT = HERE / "conversion-contract.json"
PRIMARY = HERE / "conversion-receipt.json"
READBACK = HERE / "runtime-readback-20261118.json"
OUTPUT = HERE / "independent-readback.json"


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# Integer IEEE 754 emulation. A value is (sign_bit, exact magnitude Fraction).
# --------------------------------------------------------------------------

class Format:
    def __init__(self, precision: int, emin: int, emax: int, exponent_bits: int):
        self.p, self.emin, self.emax, self.ebits = precision, emin, emax, exponent_bits

    def round(self, sign: int, magnitude: Fraction) -> tuple[int, Fraction]:
        if magnitude == 0:
            return sign, Fraction(0)
        num, den = magnitude.numerator, magnitude.denominator
        e = num.bit_length() - den.bit_length()
        if (num << max(0, -e)) < (den << max(0, e)):
            e -= 1
        e = max(e, self.emin)
        shift = self.p - 1 - e                      # magnitude * 2^shift has p bits
        top, bottom = (num << shift, den) if shift >= 0 else (num, den << -shift)
        mantissa, remainder = divmod(top, bottom)
        twice = 2 * remainder
        if twice > bottom or (twice == bottom and mantissa % 2 == 1):
            mantissa += 1
        value = Fraction(mantissa) * Fraction(2) ** (-shift)
        if value >= Fraction(2) ** (self.emax + 1):
            raise OverflowError
        return sign, value

    def to_bits(self, sign: int, value: Fraction) -> int:
        frac_bits = self.p - 1
        bias = (1 << (self.ebits - 1)) - 1
        if value == 0:
            return sign << (self.ebits + frac_bits)
        num, den = value.numerator, value.denominator
        e = num.bit_length() - den.bit_length()
        if (num << max(0, -e)) < (den << max(0, e)):
            e -= 1
        if e < self.emin:
            mant = value * Fraction(2) ** (-(self.emin - frac_bits))
            assert mant.denominator == 1
            return (sign << (self.ebits + frac_bits)) | int(mant)
        mant = value * Fraction(2) ** (frac_bits - e)
        assert mant.denominator == 1
        return (sign << (self.ebits + frac_bits)) | ((e + bias) << frac_bits) | (int(mant) - (1 << frac_bits))


B64 = Format(53, -1022, 1023, 11)
B128 = Format(113, -16382, 16383, 15)


class F:
    """A binary64 datum with its sign bit (meaningful for zero)."""
    __slots__ = ("s", "m")

    def __init__(self, s: int, m: Fraction):
        self.s, self.m = s, m

    @staticmethod
    def exact(q: Fraction) -> "F":
        return F(*B64.round(1 if q < 0 else 0, abs(Fraction(q))))

    @property
    def q(self) -> Fraction:
        return -self.m if self.s else self.m

    def bits(self) -> str:
        return "0x%016x" % B64.to_bits(self.s, self.m)

    def __neg__(self):
        return F(1 - self.s, self.m)


def _result(q: Fraction, zero_sign: int) -> F:
    if q == 0:
        return F(zero_sign, Fraction(0))
    return F(*B64.round(1 if q < 0 else 0, abs(q)))


def add(a: F, b: F) -> F:
    return _result(a.q + b.q, 1 if (a.s and b.s and a.m == 0 and b.m == 0) else 0)


def sub(a: F, b: F) -> F:
    return add(a, -b)


def mul(a: F, b: F) -> F:
    return _result(a.q * b.q, a.s ^ b.s)


def div(a: F, b: F) -> F:
    return _result(a.q / b.q, a.s ^ b.s)


def fma(a: F, b: F, c: F) -> F:
    product_sign = a.s ^ b.s
    exact = a.q * b.q + c.q
    zero_sign = 1 if (exact == 0 and a.q * b.q == 0 and c.m == 0 and product_sign and c.s) else 0
    return _result(exact, zero_sign)


def sqrt(a: F) -> F:
    if a.m == 0:
        return F(a.s, Fraction(0))
    x = a.m
    num, den = x.numerator, x.denominator
    e2 = num.bit_length() - den.bit_length()
    e = e2 // 2 - 54
    while True:
        scaled = x / Fraction(4) ** e                # sqrt(x) / 2^e = sqrt(scaled)
        n, d = scaled.numerator, scaled.denominator
        m0 = math.isqrt(n * d) // d                 # floor(sqrt(scaled))
        if m0 >= 1 << 54:
            e += 1
        elif m0 < 1 << 53:
            e -= 1
        else:
            break
    # m0 has 54 bits: round sqrt(scaled) to 53 bits by looking at sqrt(scaled) / 2
    half = Fraction(m0 // 2)
    target = scaled / 4                             # sqrt(target) = sqrt(scaled) / 2
    lower = half
    mid = lower + Fraction(1, 2)
    comparison = (target > mid * mid) - (target < mid * mid)
    mantissa = int(lower) + (1 if comparison > 0 or (comparison == 0 and int(lower) % 2) else 0)
    return F(0, Fraction(mantissa) * Fraction(2) ** (e + 1))


def from_int(n: int) -> F:
    return F.exact(Fraction(n))


# --------------------------------------------------------------------------
# Decimal text by integer digit arithmetic
# --------------------------------------------------------------------------

def exponent10(q: Fraction) -> int:
    e = len(str(q.numerator)) - len(str(q.denominator))
    while (q.numerator * 10 ** max(0, -e)) < (q.denominator * 10 ** max(0, e)):
        e -= 1
    while (q.numerator * 10 ** max(0, -(e + 1))) >= (q.denominator * 10 ** max(0, e + 1)):
        e += 1
    return e


def decimal16(q: Fraction) -> tuple[str, bool]:
    if q == 0:
        return "0", False
    a = abs(q)
    e = exponent10(a)
    k = 15 - e
    top, bottom = (a.numerator * 10 ** k, a.denominator) if k >= 0 else (a.numerator, a.denominator * 10 ** -k)
    digits, remainder = divmod(top, bottom)
    tie = 2 * remainder == bottom
    if 2 * remainder > bottom or (tie and digits % 2):
        digits += 1
    if digits == 10 ** 16:
        digits, e = 10 ** 15, e + 1
    text = str(digits)
    if e < -4 or e > 15:
        tail = text[1:].rstrip("0")
        body = text[0] + ("." + tail if tail else "") + ("e-" if e < 0 else "e+") + str(abs(e)).zfill(2)
    elif e >= 0:
        tail = text[e + 1:].rstrip("0")
        body = text[:e + 1] + ("." + tail if tail else "")
    else:
        body = "0." + ("0" * (-e - 1) + text).rstrip("0")
    return ("-" if q < 0 else "") + body, tie


def parse(text: str) -> Fraction:
    t = text.lower()
    sign = -1 if t.startswith("-") else 1
    t = t.lstrip("+-")
    mantissa, _, exponent = t.partition("e")
    whole, _, fraction = mantissa.partition(".")
    digits = int((whole + fraction) or "0")
    power = int(exponent or "0") - len(fraction)
    return sign * (Fraction(digits) * Fraction(10) ** power)


VSMALL = F.exact(parse("1e-300"))
VGREAT = F.exact(parse("1e+300"))
ROOTVSMALL = F.exact(parse("1e-150"))
CLOSED = F.exact(parse("1e-6"))
U = Fraction(1, 2 ** 53)


def gamma(k: int) -> Fraction:
    return k * U / (1 - k * U)


def native_read(text: str) -> dict:
    if len(text) >= 128:
        return {"branch": "length-refusal", "x": None}
    digits_only = text[0] != "." and all(c.isdigit() for c in text[1:]) and text != "-"
    out = {}
    if digits_only:
        value = int(text)
        if -2 ** 31 <= value <= 2 ** 31 - 1:
            return {"branch": "label", "x": from_int(value)}
        out["label_overflow"] = True
    exact = parse(text)
    sign, q = B128.round(1 if exact < 0 else 0, abs(exact))
    signed = -q if sign else q
    if -VSMALL.q <= signed <= VSMALL.q:
        out.update(branch="zero", x=F(0, Fraction(0)))
    elif signed < -VGREAT.q or signed > VGREAT.q:
        out.update(branch="range-refusal", x=None)
    else:
        x = F(*B64.round(sign, q))
        correct = F.exact(exact)
        out.update(branch="scalar", x=x, discrepancy=x.bits() != correct.bits())
    return out


def native_write(x: F) -> str:
    if x.m == 0:
        return "-0" if x.s else "0"
    return decimal16(x.q)[0]


def contract_number(text) -> Fraction:
    s = str(text).strip()
    if s.startswith("binary64(") and s.endswith(")"):
        return F.exact(parse(s[9:-1])).q
    if "^" in s:
        if "/10^" in s:
            p, k = s.split("/10^")
            return Fraction(int(p), 10 ** int(k))
        base, power = s.lstrip("-").split("^")
        return (-1 if s.startswith("-") else 1) * Fraction(int(base)) ** int(power)
    if "/" in s:
        p, q = s.split("/")
        return Fraction(int(p), int(q))
    return parse(s)


# --------------------------------------------------------------------------
# Comparison helpers
# --------------------------------------------------------------------------

class Ledger:
    def __init__(self):
        self.compared = 0
        self.mismatches: list[str] = []

    def same(self, where: str, ours, theirs):
        self.compared += 1
        if ours != theirs:
            self.mismatches.append(f"{where}: independent {ours!r} != primary {theirs!r}")


def read_witnesses(contract: dict, primary: dict, book: Ledger):
    rows = {r["id"]: r for r in primary["witnesses"]["rationals"]}
    for item in contract["witnesses"]["rationals"]:
        r = contract_number(item["value"])
        row = rows[item["id"]]
        t1, tie = decimal16(r)
        book.same(f"{item['id']}.S1", t1, row["S1"])
        book.same(f"{item['id']}.S1_tie", tie, row["S1_tie"])
        if r != 0:
            e = exponent10(abs(r))
            book.same(f"{item['id']}.S1_bound", abs(parse(t1) - r) <= Fraction(10) ** (e - 15) / 2, True)
        first = native_read(t1)
        book.same(f"{item['id']}.S2.branch", first["branch"], row["S2"]["branch"])
        if first.get("x") is not None:
            book.same(f"{item['id']}.S2.bits", first["x"].bits(), row["S2"]["x_bits"])
            if first["branch"] == "scalar":
                book.same(f"{item['id']}.S2.discrepancy", first["discrepancy"], row["S2"]["double_rounding_discrepancy"])
                book.same(f"{item['id']}.S2.bound", abs(first["x"].q - parse(t1)) <= (U + Fraction(1, 2 ** 111)) * abs(parse(t1)), True)
            t2 = native_write(first["x"])
            book.same(f"{item['id']}.S3", t2, row["S3"])
            second = native_read(t2)
            book.same(f"{item['id']}.S4.branch", second["branch"], row["S4"]["branch"])
            if second.get("x") is not None:
                book.same(f"{item['id']}.S4.bits", second["x"].bits(), row["S4"]["x_bits"])
        exact = F.exact(r) if r != 0 else None
        if exact is not None and exact.q == r and abs(r) <= VGREAT.q:
            cycle = row.get("binary64_cycle")
            text = native_write(exact)
            back = native_read(text)
            book.same(f"{item['id']}.cycle.S3", text, cycle and cycle["S3"])
            book.same(f"{item['id']}.cycle.identity", back.get("x") is not None and back["x"].bits() == exact.bits(),
                      cycle and cycle["identity"])
    texts = {t["id"]: t for t in primary["witnesses"]["texts"]}
    for item in contract["witnesses"]["texts"]:
        text = "1" * 128 if item["text"] == "repeat '1' 128 times" else item["text"]
        row = texts[item["id"]]
        first = native_read(text)
        book.same(f"{item['id']}.S2.branch", first["branch"], row["S2"]["branch"])
        book.same(f"{item['id']}.S2.label_overflow", bool(first.get("label_overflow")), bool(row["S2"].get("label_overflow")))
        if first.get("x") is not None:
            book.same(f"{item['id']}.S2.bits", first["x"].bits(), row["S2"]["x_bits"])
            if first["branch"] == "scalar":
                book.same(f"{item['id']}.S2.discrepancy", first["discrepancy"], row["S2"]["double_rounding_discrepancy"])
            t2 = native_write(first["x"])
            book.same(f"{item['id']}.S3", t2, row["S3"])
        if item["id"] == "text-minus-zero-label":
            book.same("negative-zero.S3", native_write(F(1, Fraction(0))), row["S3_of_negative_zero"])


def read_thresholds(contract: dict, primary: dict, book: Ledger) -> None:
    rows = {r["id"]: r for r in primary["thresholds"]["literals"]}
    for item in contract["thresholds"]:
        if "literal" not in item:
            continue
        value = F.exact(parse(item["literal"]))
        text = native_write(value)
        back = native_read(text)
        row = rows[item["id"]]
        book.same(f"threshold.{item['id']}.bits", value.bits(), row["bits"])
        book.same(f"threshold.{item['id']}.S3", text, row["S3"])
        book.same(f"threshold.{item['id']}.survives", back.get("x") is not None and back["x"].bits() == value.bits(),
                  row["survives_native_cycle"])
    pi = F.exact(Fraction(884279719003555, 281474976710656))      # binary64 pi = 0x400921fb54442d18
    argument = div(mul(from_int(70), pi), from_int(180))
    cosine = primary["thresholds"]["non_orthogonality_cosine"]
    book.same("cos.pi_bits", pi.bits(), cosine["pi64_bits"])
    book.same("cos.argument_bits", argument.bits(), cosine["argument_bits"])
    decimal.getcontext().prec = 120
    x = decimal.Decimal(argument.q.numerator) / decimal.Decimal(argument.q.denominator)
    term, total, k = decimal.Decimal(1), decimal.Decimal(1), 0
    while abs(term) > decimal.Decimal(10) ** -115:
        k += 1
        term = -term * x * x / ((2 * k - 1) * (2 * k))
        total += term
    value = Fraction(total)
    slack = Fraction(1, 10 ** 100)
    down, up = (Fraction(v) for v in cosine["bracket"])
    book.same("cos.bracket_encloses", down < value - slack and value + slack < up, True)
    book.same("cos.bracket_adjacent", F.exact(down).bits() == cosine["neighbour_down_bits"]
              and B64.to_bits(0, up) - B64.to_bits(0, down) == 1, True)
    nearest = down if value < (down + up) / 2 else up
    book.same("cos.nearest", F.exact(nearest).bits(), cosine["round_to_nearest_bits"])


def read_certificates(contract: dict, primary: dict, book: Ledger) -> None:
    files = {}
    for item in contract["certificates"]:
        path = REPO / item["path"]
        book.same(f"certificate.{item['id']}.sha256", sha(path), item["sha256"])
        files[item["id"]] = json.loads(path.read_text(encoding="utf-8"))
    tets = files["face-tets-summary"]
    leaves = [b["parent_leaf"] for b in tets["box_results"]]
    kept = contract["retained"]
    retained = primary["certificates"]["retained"]
    book.same("retained.boxes", len(leaves), retained["boxes"])
    book.same("retained.leaves", leaves == list(range(kept["leaves"][0], kept["leaves"][1] + 1)), True)
    book.same("retained.domain", files["dossier"]["domain_v"], kept["domain_v"])
    book.same("retained.lower", tets["box_results"][0]["lower"], kept["domain_v"][0])
    book.same("retained.upper", tets["box_results"][-1]["upper"], kept["domain_v"][1])
    book.same("retained.determinants", tets["determinant_indecisions_1929_1930_unchanged"], True)
    book.same("retained.all_kept", retained["all_kept"], True)
    flat, ortho, skew = files["flatness-summary"], files["orthogonality-summary"], files["skewness-summary"]
    weight, ratio = files["weight-summary"], files["volume-ratio-readback"]
    down, up = (Fraction(v) for v in primary["thresholds"]["non_orthogonality_cosine"]["bracket"])
    ortho_high = Fraction(files["orthogonality-readback"]["threshold"][1])
    expected = {
        "G6-flatness": Fraction(flat["minimum_positive_record_bounds"]["flatness"]["lower"]) - F.exact(parse("0.8")).q,
        "G5-non-orthogonality": Fraction(ortho["minimum_positive_certificate"]["lower"]) - max(up, ortho_high),
        "G9-skewness": 4 - Fraction(skew["maximum_positive_upper"]),
        "G7-weights": Fraction(weight["minimum_positive_lower"]) - F.exact(parse("0.05")).q,
        "G8-volume-ratio": Fraction(ratio["minimum_ratio_lower"]) - F.exact(parse("0.01")).q,
        "G1-face-guard": 2 * Fraction(flat["minimum_positive_record_bounds"]["magS"]["lower"]) - ROOTVSMALL.q,
    }
    margins = {m["criterion"]: m for m in primary["certificates"]["margins"]}
    for name, value in expected.items():
        book.same(f"margin.{name}", str(value), margins[name]["margin"])
        book.same(f"margin.{name}.undecided", margins[name]["native_decision"].startswith("undecided"), True)
    guard = primary["certificates"]["face_guard_critical_scale"]
    mags = Fraction(flat["minimum_positive_record_bounds"]["magS"]["lower"])
    eps16, eps_read = Fraction(1, 2 * 10 ** 15), U + Fraction(1, 2 ** 111)
    beta = (1 + eps16) * (1 + eps_read) - 1
    beta2 = (1 + beta) ** 2 - 1
    r2 = (2 * mags - ROOTVSMALL.q / (1 - gamma(6))) / (12 * beta2 * (2 + beta2) + 32 * gamma(4) * (2 + gamma(4)))
    r_crit = Fraction(math.isqrt(r2.numerator * 10 ** 12 // r2.denominator), 10 ** 6)
    book.same("guard.R_crit", str(r_crit), guard["R_crit_lower_bound"])
    book.same("guard.R_crit_is_lower_bound", r_crit * r_crit <= r2, True)


# --------------------------------------------------------------------------
# Reference cells, rebuilt and recomputed by emulation
# --------------------------------------------------------------------------

def read_point(exact) -> list[F]:
    out = []
    for value in exact:
        read = native_read(decimal16(value)[0])
        out.append(read["x"])
    return out


def build(contract: dict):
    spec = contract["reference_cells"]
    offset = [contract_number(v) for v in spec["offset"]]
    edge = contract_number(spec["edge"])
    a, b, c, d = (Fraction(v) for v in spec["rotation_quaternion"])
    n = a * a + b * b + c * c + d * d
    rot = [[(a * a + b * b - c * c - d * d) / n, 2 * (b * c - a * d) / n, 2 * (b * d + a * c) / n],
           [2 * (b * c + a * d) / n, (a * a - b * b + c * c - d * d) / n, 2 * (c * d - a * b) / n],
           [2 * (b * d - a * c) / n, 2 * (c * d + a * b) / n, (a * a - b * b - c * c + d * d) / n]]

    def place(v, rotate, lift=Fraction(0)):
        vec = [Fraction(v[0]), Fraction(v[1]), Fraction(v[2]) + lift]
        if rotate:
            vec = [rot[i][0] * vec[0] + rot[i][1] * vec[1] + rot[i][2] * vec[2] for i in range(3)]
        return read_point([offset[i] + edge * vec[i] for i in range(3)])

    cells = []
    for item in spec["cells"]:
        hexa = item["shape"] == "hex"
        unit = spec["hex_unit_vertices"] if hexa else spec["prism_unit_vertices"]
        rotate = item["id"] in ("RC2-rotated-cube", "RC4-rotated-prism")
        points = [place(v, rotate, Fraction(1, 10) if (item["id"] == "RC3-warped-hex" and i == 6) else Fraction(0))
                  for i, v in enumerate(unit)]
        cells.append((item["id"], points, spec["hex_faces"] if hexa else spec["prism_faces"]))
    index = {}
    for k in range(3):
        for j in range(3):
            for i in range(3):
                index[(i, j, k)] = len(index)
    lattice = [None] * 27
    for key, position in index.items():
        lattice[position] = place(key, True)
    faces, owners, neighbours, seen = [], [], [], {}
    count = 0
    for k in range(2):
        for j in range(2):
            for i in range(2):
                corners = [index[(i + x, j + y, k + z)] for x, y, z in spec["hex_unit_vertices"]]
                for local in spec["hex_faces"]:
                    face = [corners[v] for v in local]
                    key = tuple(sorted(face))
                    if key in seen:
                        neighbours[seen[key]] = count
                    else:
                        seen[key] = len(faces)
                        faces.append(face)
                        owners.append(count)
                        neighbours.append(None)
                count += 1
    internal = [f for f in range(len(faces)) if neighbours[f] is not None]
    order = internal + [f for f in range(len(faces)) if neighbours[f] is None]
    block = ([lattice[i] for i in range(27)], [faces[f] for f in order], [owners[f] for f in order],
             [neighbours[f] for f in internal], count)
    guards = []
    for item in spec["guard_faces"]:
        s = contract_number(item["square_side"])
        guards.append((item["id"], [read_point(p) for p in ([0, 0, 0], [s, 0, 0], [s, s, 0], [0, s, 0])]))
    return cells, block, guards


CYCLIC = ((1, 2), (2, 0), (0, 1))


def cross(u, v, pattern):
    out = []
    for k1, k2 in CYCLIC:
        if pattern in ("F1", "F3"):
            out.append(fma(u[k1], v[k2], -mul(u[k2], v[k1])))
        elif pattern == "F2":
            out.append(fma(-u[k2], v[k1], mul(u[k1], v[k2])))
        else:
            out.append(sub(mul(u[k1], v[k2]), mul(u[k2], v[k1])))
    return out


def norm(v, pattern):
    if pattern == "F3":
        return sqrt(fma(v[0], v[0], fma(v[1], v[1], mul(v[2], v[2]))))
    return sqrt(add(add(mul(v[0], v[0]), mul(v[1], v[1])), mul(v[2], v[2])))


HALF = F(0, Fraction(1, 2))
ZERO = F(0, Fraction(0))


def area(points, face, pattern):
    p = [points[i] for i in face]
    if len(p) == 3:
        e1 = [sub(p[1][k], p[0][k]) for k in range(3)]
        e2 = [sub(p[2][k], p[0][k]) for k in range(3)]
        return [mul(HALF, c) for c in cross(e1, e2, pattern)], None, None
    centre = list(p[0])
    for i in range(1, len(p)):
        centre = [add(centre[k], p[i][k]) for k in range(3)]
    centre = [div(c, from_int(len(p))) for c in centre]
    total, magnitude = [ZERO, ZERO, ZERO], ZERO
    for i in range(len(p)):
        nxt = p[(i + 1) % len(p)]
        u = [sub(nxt[k], p[i][k]) for k in range(3)]
        v = [sub(centre[k], p[i][k]) for k in range(3)]
        n = cross(u, v, pattern)
        total = [add(total[k], n[k]) for k in range(3)]
        magnitude = add(magnitude, norm(n, pattern))
    return [mul(HALF, t) for t in total], centre, magnitude


def exact_area(points, face):
    p = [[c.q for c in points[i]] for i in face]
    out = [Fraction(0)] * 3
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        for k, (k1, k2) in enumerate(CYCLIC):
            out[k] += a[k1] * b[k2] - a[k2] * b[k1]
    return [v / 2 for v in out]


def bound(points, face, centre):
    p = [[c.q for c in points[i]] for i in face]
    if len(p) == 3:
        e1 = [p[1][k] - p[0][k] for k in range(3)]
        e2 = [p[2][k] - p[0][k] for k in range(3)]
        return [gamma(4) / 2 * (abs(e1[k1] * e2[k2]) + abs(e1[k2] * e2[k1])) for k1, k2 in CYCLIC]
    c = [v.q for v in centre]
    totals = [Fraction(0)] * 3
    for i in range(len(p)):
        u = [p[(i + 1) % len(p)][k] - p[i][k] for k in range(3)]
        v = [c[k] - p[i][k] for k in range(3)]
        for k, (k1, k2) in enumerate(CYCLIC):
            totals[k] += abs(u[k1] * v[k2]) + abs(u[k2] * v[k1])
    return [gamma(len(p) + 3) / 2 * t for t in totals]


PATTERNS = ("F0", "F1", "F2", "F3")


def faces_check(points, faces, rows, label, book):
    computed = []
    for index, (face, row) in enumerate(zip(faces, rows)):
        exact = exact_area(points, face)
        book.same(f"{label}.face{index}.exact", hashlib.sha256(",".join(str(v) for v in exact).encode()).hexdigest(),
                  row["exact_sha256"])
        per = {}
        for pattern in PATTERNS:
            a, centre, magnitude = area(points, face, pattern)
            bnd = bound(points, face, centre)
            book.same(f"{label}.face{index}.{pattern}.bits", [v.bits() for v in a], row["patterns"][pattern]["A_bits"])
            book.same(f"{label}.face{index}.{pattern}.within", all(abs(a[k].q - exact[k]) <= bnd[k] for k in range(3)),
                      row["patterns"][pattern]["within_bound"])
            if magnitude is not None:
                book.same(f"{label}.face{index}.{pattern}.sumA", magnitude.bits(), row["patterns"][pattern]["sumA_bits"])
                book.same(f"{label}.face{index}.{pattern}.guard_computed", magnitude.q < ROOTVSMALL.q,
                          row["patterns"][pattern]["guard_computed_active"])
            per[pattern] = (a, bnd)
        computed.append((exact, per))
    return computed


def closure(computed, members, pattern, label, primary_row, book):
    s, d = [ZERO, ZERO, ZERO], [ZERO, ZERO, ZERO]
    for index, sign in members:
        a = computed[index][1][pattern][0]
        s = [add(s[k], a[k]) if sign > 0 else sub(s[k], a[k]) for k in range(3)]
        d = [add(d[k], F(0, a[k].m)) for k in range(3)]
    open_values = [div(F(0, s[k].m), add(d[k], ROOTVSMALL)) for k in range(3)]
    worst = max(open_values, key=lambda v: v.q)
    book.same(f"{label}.{pattern}.S", [v.bits() for v in s], primary_row["S_bits"])
    book.same(f"{label}.{pattern}.openness", worst.bits(), primary_row["openness_bits"])
    zero = all(sum(sign * computed[i][0][k] for i, sign in members) == 0 for k in range(3))
    book.same(f"{label}.{pattern}.exact_zero", zero, primary_row["exact_sum_is_zero"])
    m = len(members)
    holds = all(abs(s[k].q) <= sum(computed[i][1][pattern][1][k] for i, _ in members)
                + gamma(m - 1) * sum(abs(computed[i][1][pattern][0][k].q) for i, _ in members) for k in range(3))
    book.same(f"{label}.{pattern}.within", holds, primary_row["S_within_bound"])
    book.same(f"{label}.{pattern}.flagged", worst.q > CLOSED.q, primary_row["computed_flagged_open"])


def boundary(computed, members, pattern, label, primary_row, book):
    s, total = [ZERO, ZERO, ZERO], ZERO
    for index in members:
        a = computed[index][1][pattern][0]
        s = [add(s[k], a[k]) for k in range(3)]
        total = add(total, norm(a, pattern))
    values = [div(s[k], add(total, VSMALL)) for k in range(3)]
    worst = max((F(0, v.m) for v in values), key=lambda v: v.q)
    book.same(f"{label}.{pattern}.S", [v.bits() for v in s], primary_row["S_bits"])
    book.same(f"{label}.{pattern}.openness", worst.bits(), primary_row["openness_max_bits"])
    book.same(f"{label}.{pattern}.flagged", worst.q > CLOSED.q, primary_row["computed_flagged_open"])


def read_references(contract: dict, primary: dict, book: Ledger) -> None:
    cells, block, guards = build(contract)
    rows = {c["id"]: c for c in primary["references"]["cells"]}
    for name, points, faces in cells:
        row = rows[name]
        book.same(f"{name}.points", [[c.bits() for c in p] for p in points], row["points_bits"])
        computed = faces_check(points, faces, row["faces"], name, book)
        for pattern in PATTERNS:
            closure(computed, [(i, 1) for i in range(len(faces))], pattern, name + ".cell", row["closedness"][pattern], book)
            boundary(computed, list(range(len(faces))), pattern, name + ".boundary", row["boundary"][pattern], book)
    points, faces, owners, neighbours, count = block
    row = primary["references"]["block"]
    book.same("block.points", hashlib.sha256("".join(c.bits() for p in points for c in p).encode()).hexdigest(),
              row["points_sha256"])
    book.same("block.counts", (count, len(neighbours), len(faces) - len(neighbours)),
              (row["cells"], row["internal_faces"], row["boundary_faces"]))
    computed = faces_check(points, faces, row["faces"], "block", book)
    members = {c: [] for c in range(count)}
    for f, cell in enumerate(owners):
        members[cell].append((f, 1))
    for f, cell in enumerate(neighbours):
        members[cell].append((f, -1))
    for cell, faces_of_cell in members.items():
        for pattern in PATTERNS:
            closure(computed, faces_of_cell, pattern, f"block.cell{cell}", row["closedness"][str(cell)][pattern], book)
    for pattern in PATTERNS:
        boundary(computed, list(range(len(neighbours), len(faces))), pattern, "block.boundary", row["boundary"][pattern], book)
    grows = {g["id"]: g for g in primary["references"]["guards"]}
    for name, square in guards:
        g = grows[name]
        book.same(f"{name}.points", [[c.bits() for c in p] for p in square], g["points_bits"])
        faces_check(square, [[0, 1, 2, 3]], [g["face"]], name, book)


def read_runtime(primary_readback: dict, extract: Path | None, book: Ledger) -> dict:
    matrix = json.loads((REPO / "twins/bionic-turbo-f1/baseline-20261106-mac/runtime-matrix.json").read_text(encoding="utf-8"))
    row = next(r for r in matrix["rows"] if r["id"] == "opencfd-v2406-runtime")
    book.same("runtime.manifest_digest", primary_readback["oci"]["manifest_digest"], "sha256:" + row["identity"]["image"].split("@sha256:")[1])
    for name, digest in row["executables"].items():
        book.same(f"runtime.{name}", primary_readback["pinned_executables"][name]["observed"], digest)
    rehashed = {}
    if extract is not None:
        base = extract / primary_readback["platform_directory"]
        rehashed = {"checkMesh": sha(base / "bin/checkMesh"), "libOpenFOAM.so": sha(base / "lib/libOpenFOAM.so")}
        book.same("runtime.rehash.checkMesh", rehashed["checkMesh"], row["executables"]["checkMesh"])
        book.same("runtime.rehash.libOpenFOAM", rehashed["libOpenFOAM.so"], primary_readback["libraries"]["libOpenFOAM.so"])
    return rehashed


def run(extract: Path | None = None) -> dict:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    primary = json.loads(PRIMARY.read_text(encoding="utf-8"))
    readback = json.loads(READBACK.read_text(encoding="utf-8"))
    book = Ledger()
    read_witnesses(contract, primary, book)
    read_thresholds(contract, primary, book)
    read_certificates(contract, primary, book)
    read_references(contract, primary, book)
    rehashed = read_runtime(readback, extract, book)
    return {
        "schema": "bionic-turbo-fp-chain-independent-readback/v1",
        "issue": 397,
        "imports_primary": False,
        "method": "integer IEEE 754 emulation with signed zeros; integer decimal formatting and parsing; decimal-module cosine at 120 digits; certificates re-read from their pinned files",
        "contract_sha256": sha(CONTRACT),
        "primary_receipt_sha256": sha(PRIMARY),
        "readback_sha256": sha(READBACK),
        "reader_sha256": sha(Path(__file__)),
        "private_rehash": bool(rehashed),
        "comparisons": book.compared,
        "mismatches": book.mismatches,
        "status": "passed" if not book.mismatches else "failed",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--private-extract", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    result = run(args.private_extract)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        OUTPUT.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    print(f"independent reader: {result['status']} ({result['comparisons']} comparisons, "
          f"{len(result['mismatches'])} mismatches)", file=sys.stderr)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
