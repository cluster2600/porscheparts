"""Independent energy balance of a steady thermal screen.

Reads the CalculiX deck (nodes, C3D4 elements, *FILM faces), the nodal
temperatures (.frd) and the chamber reaction heat flow (.dat), then recomputes
the convective loss  sum h * A_face * (mean T_face - T_air)  over every film
face. In steady state it must equal the heat entering through the fixed-
temperature chamber nodes. Linear face temperature is integrated exactly by
the vertex mean on a triangle.

Usage: check_thermal_balance.py WORKDIR OUT.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

FACE_NODES = {1: (0, 1, 2), 2: (0, 1, 3), 3: (1, 2, 3), 4: (0, 2, 3)}


def parse_deck(inp):
    nodes, elems, films, mode = [], [], [], None
    for line in open(inp):
        if line.startswith("*"):
            key = line.upper()
            mode = ("node" if key.startswith("*NODE") and "FILE" not in key and "PRINT" not in key
                    else "elem" if key.startswith("*ELEMENT")
                    else "film" if key.startswith("*FILM") else None)
            continue
        if mode == "node":
            p = line.split(",")
            nodes.append((int(p[0]), float(p[1]), float(p[2]), float(p[3])))
        elif mode == "elem":
            p = line.split(",")
            elems.append(tuple(int(x) for x in p[1:5]))
        elif mode == "film":
            p = line.split(",")
            films.append((int(p[0]), int(p[1].strip()[1:]), float(p[2]), float(p[3])))
    return np.array(nodes), np.array(elems, dtype=np.int64), films


def read_temps(frd):
    temps, on = {}, False
    for line in open(frd):
        if line.startswith(" -4  NDTEMP"):
            on = True
            continue
        if on and line.startswith(" -1"):
            temps[int(line[3:13])] = float(line[13:25])
        elif on and line.startswith(" -3"):
            on = False
    return temps


def chamber_inflow(dat):
    lines = open(dat).read().splitlines()
    for i, line in enumerate(lines):
        if "total" in line.lower() and "nchamber" in line.lower():
            for nxt in lines[i + 1:i + 4]:
                if nxt.strip():
                    return float(nxt.split()[0])
    return None


def main(work, out):
    work = Path(work)
    nodes, elems, films = parse_deck(work / "head.inp")
    temps = read_temps(work / "head.frd")
    tag = nodes[:, 0].astype(np.int64)
    xyz = nodes[:, 1:]
    tvec = np.array([temps[int(t)] for t in tag])
    order = np.argsort(tag)
    tag, xyz, tvec = tag[order], xyz[order], tvec[order]
    f = np.array(films)
    e = f[:, 0].astype(np.int64) - 1
    fid = f[:, 1].astype(np.int64)
    tri = np.empty((len(f), 3), dtype=np.int64)
    for k, loc in FACE_NODES.items():
        sel = fid == k
        tri[sel] = elems[e[sel]][:, list(loc)]
    idx = np.searchsorted(tag, tri)
    p = xyz[idx]
    area = 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)
    loss = float((f[:, 3] * area * (tvec[idx].mean(axis=1) - f[:, 2])).sum())
    inflow = chamber_inflow(work / "head.dat")
    rep = {"film_faces": int(len(f)), "film_area_mm2": round(float(area.sum()), 1),
           "convective_loss_W": round(loss, 4), "chamber_inflow_W": inflow,
           "relative_imbalance": (round(abs(abs(inflow) - loss) / loss, 6) if inflow else None)}
    Path(out).write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:3])
