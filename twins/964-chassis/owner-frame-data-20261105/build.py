#!/usr/bin/env python3
"""Check documentary coordinate arithmetic; publish no donor geometry."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def source_coordinates(data: dict) -> list[dict]:
    rows = []
    for state, sheet in data["ch"]["states"].items():
        station = 0
        for index, key in enumerate(sheet["chain_point_ids"]):
            if index:
                station += sheet["chain_increments"][index - 1]
            point = sheet["points"][key]
            if station != point["x_relative_to_point5"]:
                raise ValueError(f"CH {state}/{key}: coordinate disagrees with projected chain")
            rows.append(dict(family="CH", state=state, point=key, x=station,
                             half_width=point["half_width"], height=point["height"]))
    # Direction is read from the front-to-rear side view, not a direct diagonal.
    positions = {"F": 0}
    edges = data["mi"]["longitudinal_projections"]
    while True:
        before = len(positions)
        for edge in edges:
            a, b, value = edge["from"], edge["to"], edge["printed_value"]
            if a in positions:
                candidate = positions[a] + value
                if b in positions and positions[b] != candidate:
                    raise ValueError("Mi contradictory longitudinal projection")
                positions[b] = candidate
            elif b in positions:
                positions[a] = positions[b] - value
        if len(positions) == before:
            break
    for point in data["mi"]["points"]:
        key = point["point_id"]
        if key not in positions:
            raise ValueError(f"Mi disconnected point {key}")
        for contact, height in point["height_above_printed_datum_line"].items():
            rows.append(dict(family="Mi", state=contact, point=key, x=positions[key],
                             half_width=point["half_width_if_equal_sides"], height=height))
    return rows


def distance(a: dict, b: dict, cross: bool) -> float:
    if a["half_width"] is None or b["half_width"] is None:
        raise ValueError("Unknown transverse coordinate cannot supply a spatial distance")
    dy = a["half_width"] + b["half_width"] if cross else a["half_width"] - b["half_width"]
    return math.sqrt((a["x"] - b["x"]) ** 2 + dy ** 2 + (a["height"] - b["height"]) ** 2)


def audit(data: dict) -> tuple[dict, list[dict]]:
    rows = source_coordinates(data)
    checks = []
    for state, sheet in data["ch"]["states"].items():
        points = {r["point"]: r for r in rows if r["family"] == "CH" and r["state"] == state}
        for span in sheet["checks"]:
            measured = distance(points[str(span["from"])], points[str(span["to"])], span["kind"] == "cross")
            checks.append(dict(family="CH", state=state, **span, computed=measured,
                               residual=measured - span["printed_mm"]))
    # These six spans use A/F/G/J only; each has one unambiguous contact height.
    points = {r["point"]: r for r in rows if r["family"] == "Mi" and r["point"] in "AFGJ"}
    for span in data["mi"]["point_to_point_spans"]:
        cross = span["relation"] == "opposite_side_diagonal_pair"
        measured = distance(points[span["from"]], points[span["to"]], cross)
        checks.append(dict(family="Mi", state="specified_contacts", **span,
                           computed=measured, residual=measured - span["printed_value"]))
    for check in checks:
        check["rounding_consistent"] = abs(check["residual"]) < 0.5
    if not all(c["rounding_consistent"] for c in checks):
        raise ValueError("A source-local spatial check does not round to its printed integer")
    return dict(status="documentary_arithmetic_checked", checks=checks,
                max_absolute_residual=max(abs(c["residual"]) for c in checks),
                residual_interpretation="Rounded nominal arithmetic only; not accuracy or uncertainty",
                coordinate_rows=len(rows), donor_registration=None, functional_geometry_admitted=False,
                tunnel_surface_acquired=False, manufacturing_authorized=False), rows


def plot(rows: list[dict]) -> str:
    # Only source measurement landmarks are drawn. No body contour is inferred.
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="570" viewBox="0 0 1200 570">',
           '<rect width="1200" height="570" fill="#f7f9fb"/>',
           '<g font-family="sans-serif" fill="#182d42">',
           '<text x="38" y="32" font-size="22">964 CH source-local measurement landmarks</text>',
           '<text x="38" y="56" font-size="14">Separate contact states; source units interpreted as mm; no scan registration</text>']
    for index, state in enumerate(("parts_on", "parts_removed")):
        top = 90 + index * 225
        out.append(f'<text x="38" y="{top}" font-size="17">{state.replace("_", " ")}</text>')
        for row in rows:
            if row["family"] != "CH" or row["state"] != state:
                continue
            x = 70 + row["x"] * 0.27
            for sign in (-1, 1):
                y = top + 100 + sign * row["half_width"] * 0.09
                out.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="3.5" fill="#116d8e"/>')
            if row["point"] in ("5", "9", "11", "15"):
                y = top + 94 - row["half_width"] * 0.09
                out.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="12">{row["point"]}</text>')
        out.append(f'<path d="M70 {top+100}H1110" stroke="#bac9d3" stroke-dasharray="4 4"/>')
    out.extend(['<text x="38" y="548" font-size="13">Point numbers belong to CH PO10E. Lines of structural members and hidden surfaces are not supplied.</text>', '</g></svg>'])
    return "\n".join(out) + "\n"


def products(data: dict) -> dict[str, str]:
    result, rows = audit(data)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["family", "state", "point", "x", "half_width", "height"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return {"closure.json": json.dumps(result, indent=2) + "\n",
            "source-coordinates.csv": stream.getvalue(), "source-frame.svg": plot(rows)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((HERE / "source-data.json").read_text())
    for name, content in products(data).items():
        path = HERE / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                raise SystemExit(f"Stale documentary output: {name}")
        else:
            path.write_text(content)
    print("Checked 18 source-local spatial redundancies; donor geometry admission remains open.")


if __name__ == "__main__":
    main()
