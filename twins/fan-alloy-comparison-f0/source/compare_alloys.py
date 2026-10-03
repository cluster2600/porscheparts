#!/usr/bin/env python3
"""Prepare and read uniform-material elastic screens; preserve simulation provenance."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def positive(value):
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError("Expected a positive finite number")
    return value


def scale_factors(rho, young, rpm, scale=1., reference_rho=2.67,
                  reference_young=70., reference_rpm=10000.):
    for value in (rho, young, rpm, scale, reference_rho, reference_young, reference_rpm):
        positive(value)
    r = rho / reference_rho
    e = young / reference_young
    w = (rpm / reference_rpm) ** 2
    # Same topology, geometrically similar boundaries, uniform material and common Poisson ratio.
    return {"mass": r * scale**3, "inertia": r * scale**5,
            "centrifugal_stress": r * w * scale**2,
            "centrifugal_displacement": r / e * w * scale**3,
            "unprestressed_frequency": math.sqrt(e / r) / scale}


def load_cards(path):
    data = json.loads(path.read_text())
    nu = data["poisson_ratio_common_assumed"]
    if not -1 < nu < .5:
        raise ValueError("Invalid Poisson ratio")
    ids = []
    for c in data["materials"]:
        positive(c["density_g_cm3"]); positive(c["young_modulus_GPa"])
        if c["tensile_yield_comparator_MPa"] is not None:
            positive(c["tensile_yield_comparator_MPa"])
        ids.append(c["id"])
        if not re.fullmatch(r"[a-z0-9]+", c["id"]):
            raise ValueError("Invalid material identifier")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate material identifier")
    return data


def prepare(source, cards_path, output, rpm=10000.):
    positive(rpm)
    cards = load_cards(cards_path)
    text = gzip.decompress(source.read_bytes()).decode() if source.suffix == ".gz" else source.read_text()
    before = text.split("*MATERIAL", 1)[0]
    # This adapter deliberately accepts only the existing fixed-bore rotor deck.
    if ("*NSET,NSET=BORE" not in before or "*ELEMENT, type=C3D10, ELSET=Volume1" not in before
            or "*ELSET,ELSET=ROTOR" not in before):
        raise ValueError("Expected the audited quadratic fixed-bore rotor mesh")
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for card in cards["materials"]:
        case = output / card["id"]; case.mkdir()
        base = before + (f"*MATERIAL,NAME=SCREEN\n*ELASTIC\n{card['young_modulus_GPa']*1000:.12g},"
                         f"{cards['poisson_ratio_common_assumed']}\n*DENSITY\n{card['density_g_cm3']*1e-9:.12g}\n"
                         "*SOLID SECTION,ELSET=ROTOR,MATERIAL=SCREEN\n*BOUNDARY\nBORE,1,3\n")
        static = (base + "*STEP\n*STATIC\n*DLOAD\n"
                  f"ROTOR,CENTRIF,{(rpm*math.pi/30)**2:.12g},0,0,0,0,0,1\n"
                  "*NODE PRINT,NSET=Nall\nU\n*EL PRINT,ELSET=ROTOR\nS\n*END STEP\n")
        # Nall is supplied by the gmsh deck. Check rather than silently producing incomplete results.
        if "NSET=Nall" not in before:
            static = static.replace("NSET=Nall", "NSET=ALLNODES")
            ids = []; active = False
            for line in before.splitlines():
                if line.startswith("*"):
                    active = line.upper() == "*NODE"
                elif active and line.strip():
                    ids.append(line.split(",")[0])
            node_set = "*NSET,NSET=ALLNODES\n" + "\n".join(",".join(ids[i:i+12]) for i in range(0,len(ids),12)) + "\n"
            static = static.replace("*MATERIAL", node_set + "*MATERIAL", 1)
        (case / "rotor.inp").write_text(static)
        (case / "modal.inp").write_text(base + "*STEP\n*FREQUENCY\n12\n*END STEP\n")
        records.append({"id": card["id"], "rpm": rpm, "material_card": card,
                        "rotor_deck_sha256": sha(case / "rotor.inp"),
                        "modal_deck_sha256": sha(case / "modal.inp")})
    record = {"source_deck_sha256": sha(source), "material_cards_sha256": sha(cards_path),
              "units": "mm,N,s,tonne", "cases": records,
              "boundary": "inherited unmeasured bore, translations fixed; no shaft contact",
              "mesh_independence_demonstrated": False, "physical_validation": False}
    (output / "preparation.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def static_results(case, expected_hash):
    if sha(case / "rotor.inp") != expected_hash:
        raise ValueError("Deck changed after preparation")
    log = (case / "log.rotor").read_text()
    if "Job finished" not in log or "*ERROR" in log:
        raise ValueError("Incomplete or failed solver run")
    stresses, displacements = {}, {}
    active = ""
    for line in (case / "rotor.dat").read_text().splitlines():
        if "stresses" in line and "sxx" in line:
            active = "stress"; continue
        if "displacements" in line and "vx" in line:
            active = "disp"; continue
        f = line.split()
        if not f or not f[0].isdigit():
            continue
        if active == "stress" and len(f) == 8:
            xx,yy,zz,xy,xz,yz = map(float,f[2:])
            vm = math.sqrt(.5*((xx-yy)**2+(yy-zz)**2+(zz-xx)**2)+3*(xy*xy+xz*xz+yz*yz))
            key = int(f[0]); stresses[key] = max(vm, stresses.get(key,0.))
        elif active == "disp" and len(f) == 4:
            displacements[int(f[0])] = math.sqrt(sum(float(x)**2 for x in f[1:]))
    # Match output coverage to the deck, including all nodes and all quadratic elements.
    elements, nodes = 0, 0; active = ""
    for line in (case / "rotor.inp").read_text().splitlines():
        if line.startswith("*"):
            active = "node" if line == "*NODE" else "element" if line.startswith("*ELEMENT") else ""
        elif line.strip():
            nodes += active == "node"; elements += active == "element"
    if len(stresses) != elements or len(displacements) != nodes:
        raise ValueError(f"Incomplete output coverage: {len(stresses)}/{elements} elements, {len(displacements)}/{nodes} nodes")
    if not all(math.isfinite(x) for x in [*stresses.values(), *displacements.values()]):
        raise ValueError("Non-finite solver output")
    return {"von_mises_max_MPa": max(stresses.values()),
            "maximum_displacement_mm": max(displacements.values()),
            "elements": elements, "nodes": nodes,
            "solver_version": re.search(r"Version ([0-9.]+)", log)[1],
            "output_sha256": {p: sha(case/p) for p in ("rotor.dat", "log.rotor")}}


def modal_results(case, expected_hash):
    if sha(case/"modal.inp") != expected_hash:
        raise ValueError("Modal deck changed")
    log = (case/"log.modal").read_text()
    if "Job finished" not in log or "*ERROR" in log:
        raise ValueError("Modal solve did not complete")
    modes = []
    for line in (case/"modal.dat").read_text().split("P A R T I C I P A T I O N")[0].splitlines():
        f = line.split()
        if len(f) == 5 and f[0].isdigit():
            eigen, omega, freq, imag = map(float,f[1:])
            if not all(math.isfinite(x) for x in (eigen,omega,freq,imag)) or min(eigen,omega,freq)<=0 or imag!=0:
                raise ValueError("Invalid eigenvalue")
            if not math.isclose(omega,2*math.pi*freq,rel_tol=1e-6):
                raise ValueError("Frequency unit mismatch")
            modes.append(freq)
    if len(modes) != 12:
        raise ValueError("Expected twelve modes")
    return modes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source",type=Path); ap.add_argument("cards",type=Path)
    ap.add_argument("output",type=Path); ap.add_argument("--rpm",type=float,default=10000.)
    args=ap.parse_args(); prepare(args.source,args.cards,args.output,args.rpm)
    print("Prepared three conditional material cases; no physical validation")


if __name__ == "__main__":
    main()
