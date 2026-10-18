"""Independent serial-bar birth/history/release reference; no physical qualification."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


SOURCE = Path(__file__).resolve().parent
COMPONENTS = ("xx", "yy", "zz", "xy", "xz", "yz")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def references(card):
    """Uniaxial J2 return followed by equal-length serial force equilibrium."""
    E, Y = card["E_MPa"], card["yield_MPa"]
    p = card["preload_strain"] - Y / E
    eb = card["birth_strain"]
    theta = card["alpha_per_K"] * (card["cold_T_K"] - card["initial_T_K"])
    result = []
    for step in range(7):
        born, cold = step >= 3, step >= 4
        plastic = p if step else 0.0
        thermal = theta if cold else 0.0
        sigma = (0.0, Y, E * (eb-p), E * (eb-p)/2,
                 E * ((eb-p)/2-theta), 0.0, 0.0)[step]
        ea = plastic + sigma / E + thermal
        eb_physical = eb + sigma / E + thermal if born else None
        result.append(dict(time_s=step, born=born, temperature_K=260.0 if cold else 300.0,
            sigma_MPa=sigma, plastic_A=plastic, plastic_B=0.0,
            physical_axial_strain_A=ea, physical_axial_strain_B=eb_physical,
            physical_transverse_strain=-plastic/2+thermal,
            thermal_strain=thermal,
            end_displacement_mm=10*(ea+eb_physical) if born else 10*ea,
            active_elements=4 if born else 2, active_nodes=20 if born else 12))
    return result


def node_reference(state, x, y, z):
    ea, eb = state["physical_axial_strain_A"], state["physical_axial_strain_B"]
    uz = ea*z if z <= 10 else ea*10+eb*(z-10)
    lateral = state["physical_transverse_strain"]
    return dict(disp_x=lateral*x, disp_y=lateral*y, disp_z=uz,
                temperature=state["temperature_K"])


def tensor_reference(state, segment):
    p = state["plastic_A"] if segment == "A" else 0.0
    sigma = state["sigma_MPa"]
    elastic = sigma/1000
    mechanical = dict(xx=-p/2, yy=-p/2, zz=p+elastic, xy=0., xz=0., yz=0.)
    total = {k: v+(state["thermal_strain"] if k in ("xx", "yy", "zz") else 0.)
             for k, v in mechanical.items()}
    plastic = dict(xx=-p/2, yy=-p/2, zz=p, xy=0., xz=0., yz=0.)
    stress = dict(xx=0., yy=0., zz=sigma, xy=0., xz=0., yz=0.)
    return {prop+"_"+component: tensor[component]
            for prop, tensor in (("stress", stress), ("plastic_strain", plastic),
                                 ("mechanical_strain", mechanical), ("total_strain", total))
            for component in COMPONENTS}


def rows(path):
    with Path(path).open(newline="") as stream:
        data = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    if not data or any(not math.isfinite(v) for row in data for v in row.values()):
        raise ValueError("Complete finite native rows required")
    return data


def assess(directory, contract_path):
    directory, contract_path = Path(directory), Path(contract_path)
    frozen = json.loads(contract_path.read_text())
    card = json.loads((directory/"card.json").read_text())
    native = json.loads((directory/"native-execution.json").read_text())
    checks = []

    def require(condition, label):
        if not condition:
            raise ValueError(label)
        checks.append(label)

    require(card == frozen["card"], "card equals frozen contract")
    require(sha(directory/"card.json") == frozen["card_sha256"], "native card hash")
    require(sha(directory/"mechanical-birth.i") == frozen["input_sha256"], "native input hash")
    require(sha(directory/"frozen-contract.json") == sha(contract_path), "native contract bytes")
    require(sha(__file__) == frozen["assessor_sha256"], "frozen independent checker")
    require(references(card) == frozen["references"], "frozen analytical reference history")
    require(frozen["full_tensor_references"] == [
        {s:tensor_reference(h,s) for s in ("A","B") if s == "A" or h["born"]}
        for h in frozen["references"]], "frozen full tensor references")
    require(frozen["full_nodal_end_references"] == [[
        dict(x=x,y=y,z=z,**node_reference(h,x,y,z)) for x in (0.,1.) for y in (0.,1.)
        for z in ((0.,5.,10.,15.,20.) if h["born"] else (0.,5.,10.))]
        for h in frozen["references"]], "frozen full nodal references")
    require(card == json.loads((SOURCE/"card.json").read_text()), "fixed hypothetical model card")
    require(frozen["created_unix"] < native["started_unix"], "contract predates native execution")
    require(native["returncode"] == 0 and native["binary_unchanged"] and native["inputs_unchanged"],
            "successful native execution with unchanged inputs/runtime")
    require(native["binary_sha256"] == card["native_binary_sha256"], "exact pinned binary")
    require(native["network"] == "none" and native["rootfs"] == "read_only"
            and native["deadline_seconds"] == 100, "bounded isolated native execution")
    for name, digest in native["artifact_sha256"].items():
        require(Path(name).name == name and sha(directory/name) == digest, "native artifact "+name)
    for name in ("card.json", "mechanical-birth.i", "frozen-contract.json"):
        require(native["input_sha256"].get(name) == sha(directory/name), "native input manifest "+name)
    require("167ee97" in (directory/"native.log").read_text(), "native source revision in log")
    tol = card["tolerances"]
    comparisons = 0
    max_errors = {k: 0. for k in ("displacement_mm", "strain", "stress_MPa", "force_N", "temperature_K")}

    def close(actual, expected, unit, label):
        nonlocal comparisons
        if not math.isfinite(actual) or not math.isfinite(expected):
            raise ValueError("Nonfinite comparison: "+label)
        error = abs(actual-expected)
        max_errors[unit] = max(max_errors[unit], error)
        require(error <= tol[unit], label)
        comparisons += 1

    history = frozen["references"]
    for step, state in enumerate(history):
        end = rows(directory/f"mechanical_end_{step:04d}.csv")
        begin = rows(directory/f"mechanical_begin_{step:04d}.csv")
        fields = rows(directory/f"mechanical_fields_{step:04d}.csv")
        require(len(end) == state["active_nodes"] == len(begin), f"active node count {step}")
        require(len(fields) == 8*state["active_elements"], f"all active quadrature points {step}")
        expected_nodes = {(x,y,z) for x in (0.,1.) for y in (0.,1.)
                          for z in ((0.,5.,10.,15.,20.) if state["born"] else (0.,5.,10.))}
        for phase, data in (("begin",begin),("end",end)):
            require({(r["x"],r["y"],r["z"]) for r in data} == expected_nodes,
                    f"exact reference node positions {step} {phase}")
            for row in data:
                x,y,z = row["x"],row["y"],row["z"]
                if phase == "end" or not step:
                    expected = node_reference(state,x,y,z)
                elif step == 3 and z > 10:
                    expected = dict(disp_x=-.001*x,disp_y=-.001*y,disp_z=.0025*z,
                                    temperature=state["temperature_K"])
                else:
                    expected = node_reference(history[step-1],x,y,z)
                    expected["temperature"] = state["temperature_K"]
                for name,value in expected.items():
                    close(row[name],value,"temperature_K" if name == "temperature" else "displacement_mm",
                          f"{phase} {step} node{int(row['id'])} {name}")
        require({(int(r["elem_id"]),int(r["qp_id"])) for r in fields} ==
                {(e,q) for e in range(state["active_elements"]) for q in range(8)},
                f"complete unique element/quadrature indices {step}")
        for row in fields:
            e = int(row["elem_id"])
            for axis, middle, half in (("x",.5,.5),("y",.5,.5),("z",5*e+2.5,2.5)):
                require(min(abs(row[axis]-(middle-half/math.sqrt(3))),
                            abs(row[axis]-(middle+half/math.sqrt(3)))) <= tol["displacement_mm"],
                        f"declared Gauss position {step} {e} {row['qp_id']} {axis}")
            segment = "A" if row["z"] < 10 else "B"
            for name,value in tensor_reference(state,segment).items():
                close(row[name],value,"stress_MPa" if name.startswith("stress_") else "strain",
                      f"quadrature field {step} {e} {row['qp_id']} {name}")
        support_z = 10 if step < 3 else 20
        sigma = state["sigma_MPa"]
        for row in end:
            for name in ("rx","ry"):
                close(row[name],0.,"force_N",f"lateral nodal force {step} {row['id']} {name}")
            # Each unit-area end face has four nodes and uniform axial traction.
            expected = -sigma/4 if row["z"] == 0 else sigma/4 if row["z"] == support_z else 0.
            close(row["rz"],expected,"force_N",f"axial nodal force {step} {row['id']}")
        base = sum(r["rz"] for r in end if r["z"] == 0)
        top = sum(r["rz"] for r in end if r["z"] == support_z)
        close(base+top,0.,"force_N",f"independent support force balance {step}")
        close(top,sigma,"force_N",f"reaction equals section stress times unit area {step}")
    return dict(schema_version="1.0.0", status="hypothetical_mechanical_birth_release_verified",
        passed=True, checks_count=len(checks), field_comparisons=comparisons, max_absolute_errors=max_errors,
        contract_sha256=sha(contract_path), native_receipt_sha256=sha(directory/"native-execution.json"),
        assessor_sha256=sha(__file__), references=history, qualification=card["qualification"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with args.output.open("x") as stream:
        json.dump(assess(args.directory,args.contract),stream,indent=2);stream.write("\n")
