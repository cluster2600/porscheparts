#!/usr/bin/env python3
"""Build hypothetical 917 prototypes and independently check geometry and motion."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "source"))
from reconstruct import check_output, check_voxels, save, sha256
sys.path.insert(0, str(ROOT / "twins/reference-917-engine/source"))
from kinematics_f2_math import slider_delta_mm
WITNESS = ROOT / "twins/m64-cylinder-head/source/picogk-local-junction"
sys.path.insert(0, str(WITNESS))
from exact_zero_countertrial import countertrial


def validate(config):
    if config["classification"] != "hypothesis_only_not_identified_or_measured_engine":
        raise ValueError("Explicit hypothesis classification required")
    d = config["dimensions_mm"]
    values = list(d.values()) + [config["assumed_mm_per_scan_unit"]]
    for group in ("rpm_cases", "peak_pressure_bar_cases", "rod_length_sensitivity_mm"):
        values += config[group]
        if not config[group]:
            raise ValueError("Empty experiment grid")
    values += [v["assumed_density_kg_m3"] for v in config["candidate_materials"].values()]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in values):
        raise ValueError("Positive finite hypothesis values required")
    if (d["rod_length"] <= d["stroke"]/2 or min(config["rod_length_sensitivity_mm"]) <= d["stroke"]/2
            or not 0 <= config["rod_reciprocating_mass_fraction"] <= 1
            or not d["fin_diameter"] > d["cylinder_outer_diameter"] > d["bore"] > d["piston_diametral_clearance"]
            or not d["pin_inner_diameter"] < d["pin_outer_diameter"] < d["rod_small_outer_diameter"]
            or d["rod_big_bore"] >= d["rod_big_outer_diameter"]
            or d["piston_skirt_thickness"] >= (d["bore"]-d["piston_diametral_clearance"])/2
            or d["piston_crown_thickness"] >= d["piston_height"]
            or not d["rod_width"]/2 < d["piston_boss_inner_x"] < d["pin_length"]/2
            or not d["pin_outer_diameter"] < d["piston_boss_outer_diameter"] < d["piston_height"]
            or d["fin_thickness"] >= d["fin_pitch"]):
        raise ValueError("Inconsistent hypothetical dimensions")
    n = config["fin_count"]
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 100:
        raise ValueError("Invalid fin count")
    if d["fin_start"] + (n-1)*d["fin_pitch"] + d["fin_thickness"] > d["cylinder_length"]:
        raise ValueError("Fins extend outside the hypothetical cylinder")
    phases = config["crank_pair_phases_deg"]
    if len(phases) != 6 or any(isinstance(v, bool) or not math.isfinite(v) or not 0 <= v < 360 for v in phases):
        raise ValueError("Six finite crank-pair phase hypotheses required")
    return d


def position(d, angle, sign):
    r, length = d["stroke"]/2, d["rod_length"]
    t = math.radians(angle)
    y, z = r*math.cos(t), r*math.sin(t)
    return y, z, y + sign*math.sqrt(length*length-z*z)


def acceleration(d, angle, sign):
    """Second derivative with respect to crank angle, in mm/radian²."""
    r, length = d["stroke"]/2, d["rod_length"]
    t = math.radians(angle)
    root = math.sqrt(length*length-r*r*math.sin(t)**2)
    return -r*math.cos(t)-sign*(r*r*math.cos(2*t)/root+r**4*math.sin(t)**2*math.cos(t)**2/root**3)


def motion_report(config):
    d = validate(config)
    records = []
    max_closure = 0.0
    for sign in (-1, 1):
        samples = [position(d, angle, sign) for angle in range(361)]
        travel = max(p[2] for p in samples)-min(p[2] for p in samples)
        max_closure = max(max_closure, max(abs(math.hypot(p[2]-p[0], p[1])-d["rod_length"]) for p in samples))
        if not math.isclose(travel, d["stroke"], abs_tol=1e-9) or max_closure > 1e-9:
            raise ValueError("Hypothetical slider-crank does not close")
        if sign == 1 and any(abs(p[2]-(d["rod_length"]+d["stroke"]/2)-slider_delta_mm(a,d["stroke"]/2,d["rod_length"])) > 1e-9
                             for a,p in enumerate(samples)):
            raise ValueError("Existing slider-crank helper disagrees")
        records.append({"bank_sign": sign, "travel_mm": travel})
    sensitivities = []
    for length in config["rod_length_sensitivity_mm"]:
        low = length-d["stroke"]/2-d["piston_height"]/2
        high = length+d["stroke"]/2+d["piston_height"]/2
        residual = min(low-d["cylinder_base"], d["cylinder_base"]+d["cylinder_length"]-high)
        sensitivities.append({"rod_length_mm": length, "minimum_axial_skirt_coverage_residual_mm": residual,
                              "hypothesis_consistent_with_full_skirt_coverage": residual >= 0,
                              "scope": "axial_geometry_only_not_operating_clearance_or_CAD_rebuild"})
    return {"banks": records, "maximum_rod_closure_error_mm": max_closure,
            "rod_length_sensitivity": sensitivities, "crankpins_shared_between_opposed_banks": True,
            "factory_phases_or_firing_order_verified": False}


def inspect(mesh, name, d, fin_count):
    import numpy as np
    probes = {
        "cylinder": ([[0,d["cylinder_length"]/2,0]], [[(d["bore"]+d["cylinder_outer_diameter"])/4,d["cylinder_length"]/2,0]]),
        "piston": ([[0,0,0],[0,-d["piston_height"]/4,0]],
                   [[0,d["piston_height"]/2-d["piston_crown_thickness"]/2,0],
                    [0,-d["piston_height"]/4,(d["bore"]-d["piston_diametral_clearance"]-d["piston_skirt_thickness"])/2],
                    [(d["piston_boss_inner_x"]+d["pin_length"]/2)/2,0,(d["pin_outer_diameter"]+d["piston_boss_outer_diameter"])/4]]),
        "rod": ([[0,0,0],[0,d["rod_length"],0]], [[0,d["rod_length"]/2,0]]),
        "pin": ([[0,0,0]], [[0,(d["pin_outer_diameter"]+d["pin_inner_diameter"])/4,0]])
    }
    outside, inside = probes[name]
    passed = (len(mesh.faces) > 0 and np.isfinite(mesh.vertices).all() and mesh.is_watertight
              and mesh.is_winding_consistent and mesh.volume > 0 and not np.any(mesh.area_faces == 0)
              and len(mesh.split(only_watertight=False, repair=False)) == 1
              and not mesh.contains(outside).any() and mesh.contains(inside).all())
    if not passed:
        raise ValueError("Independent geometry/hole probe rejection: " + name)
    result = {"mesh_volume_mm3_hypothetical": float(mesh.volume), "triangles": len(mesh.faces),
              "watertight": True, "single_component": True, "hole_and_material_probes_passed": True}
    if name in ("cylinder", "pin"):
        if name == "cylinder":
            ideal = math.pi/4*((d["cylinder_outer_diameter"]**2-d["bore"]**2)*d["cylinder_length"]
                              +(d["fin_diameter"]**2-d["cylinder_outer_diameter"]**2)*d["fin_thickness"]*fin_count)
        else:
            ideal = math.pi/4*(d["pin_outer_diameter"]**2-d["pin_inner_diameter"]**2)*d["pin_length"]
        result["analytic_volume_mm3_hypothetical"] = ideal
        result["relative_volume_error_vs_ideal"] = abs(mesh.volume/ideal-1)
    return result


def exact_zero_candidate(raw):
    """Reuse the existing numerical witness; keep all nonzero faces and coordinates."""
    import numpy as np
    import trimesh
    trial = countertrial(raw)
    if not trial["audit"]["strict_raw_mesh_screen_pass"] or trial["remaining_duplicate_face_groups"]:
        raise ValueError("Exact-zero-only countertrial rejected; no further repair allowed")
    vertices, inverse = np.unique(raw.vertices, axis=0, return_inverse=True)
    faces = inverse[raw.faces]
    cross = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    candidate = trimesh.Trimesh(vertices,faces[np.any(cross != 0,axis=1)],process=False)
    import hashlib
    digest = hashlib.sha256(np.asarray(vertices[candidate.faces],dtype="<f8").tobytes()).hexdigest()
    if digest != trial["remaining_oriented_faces_sha256"]:
        raise ValueError("Candidate differs from independent countertrial")
    return candidate,trial


def interference_report(meshes, d):
    import numpy as np
    # shortcut: sampled small-end witnesses only; replace with swept clearance checks after internal geometry is defined.
    offset = (d["pin_outer_diameter"]+d["rod_small_outer_diameter"])/4
    rod_point = [[0,d["rod_length"]+offset,0]]
    if not meshes["rod"].contains(rod_point).all():
        raise ValueError("Interference witness is outside rod material")
    witnesses = []
    for angle in (0,45,90,135,180,225,270,315):
        for sign in (-1,1):
            y,z,wrist = position(d,angle,sign)
            piston_point = np.array([0,sign*(wrist-y),-sign*z])*offset/d["rod_length"]
            witnesses.append({"angle_deg":angle,"bank_sign":sign,
                              "rod_small_end_inside_piston_material":bool(meshes["piston"].contains([piston_point])[0])})
    return {"scope":"sampled_small_end_material_points_not_complete_swept_volume_or_clearance_check",
            "witnesses":witnesses,"assembly_interference_screen_pass":not any(w["rod_small_end_inside_piston_material"] for w in witnesses)}


def run(config_path, output, dotnet, voxels):
    import numpy as np
    import trimesh
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text())
    d = validate(config)
    motion = motion_report(config)
    output, voxels = check_output(output), check_voxels(voxels)
    config_hash = sha256(config_path)
    source_hashes = {name: sha256(HERE/name) for name in ("Program.cs","Prototype.csproj","run.py")}
    witness_hashes = {name: sha256(WITNESS/name) for name in ("exact_zero_countertrial.py","audit_mesh.py")}
    os.umask(0o077)
    output.mkdir(parents=True)
    save(output/"status.json", {"status": "running_hypothesis", "manufacturing_authorized": False})
    try:
        app = output/"app"
        with (output/"build.log").open("x") as log:
            subprocess.run([dotnet,"build",str(HERE/"Prototype.csproj"),"-c","Release","-o",str(app),
                            "-p:BaseIntermediateOutputPath="+str(output/"obj")+os.sep],stdout=log,stderr=subprocess.STDOUT,check=True)
        levels = []
        for voxel in voxels:
            target = output/f"voxel-{voxel:g}"
            print(f"PicoGK hypothetical prototypes: {voxel:g} mm grid",flush=True)
            with (output/f"voxel-{voxel:g}.log").open("x") as log:
                subprocess.run([dotnet,str(app/"Prototype.dll"),str(config_path),config_hash,str(voxel),str(target)],
                               stdout=log,stderr=subprocess.STDOUT,check=True)
            receipt = json.loads((target/"receipt.json").read_text())
            if receipt["assumptions_sha256"] != config_hash or receipt["voxel_mm"] != voxel:
                raise ValueError("Native receipt input mismatch")
            audits, meshes = {}, {}
            for name, artifact in receipt["prototypes"].items():
                for ext in ("stl","vdb"):
                    if sha256(target/f"{name}.{ext}") != artifact[f"{ext}_sha256"]:
                        raise ValueError("Native geometry hash mismatch")
                raw = trimesh.load_mesh(target/f"{name}.stl",process=False)
                meshes[name],trial = exact_zero_candidate(raw)
                audits[name] = inspect(meshes[name],name,d,config["fin_count"])
                cleaned = target/f"{name}-exact-zero-only.stl"
                meshes[name].export(cleaned)
                audits[name]["countertrial"] = trial
                audits[name]["derived_stl_sha256"] = sha256(cleaned)
                audits[name]["native_stl_rejected_for_zero_faces"] = trial["removed_zero_cross_product_faces"] > 0
            save(target/"independent-audit.json",audits)
            levels.append({"voxel_mm":voxel,"receipt":receipt,"audit":audits})
        if set(meshes) != {"cylinder","piston","rod","pin"}:
            raise ValueError("Incomplete prototype family set")
        interference = interference_report(meshes,d)
        instances, parts = [], []
        x_positions = [-d["central_pitch"]/2-2*d["regular_pitch"],-d["central_pitch"]/2-d["regular_pitch"],-d["central_pitch"]/2,
                       d["central_pitch"]/2,d["central_pitch"]/2+d["regular_pitch"],d["central_pitch"]/2+2*d["regular_pitch"]]
        for pair,(x,phase) in enumerate(zip(x_positions,config["crank_pair_phases_deg"])):
            for sign in (-1,1):
                x_bank = x-sign*d["bank_stagger"]/2
                y,z,wrist = position(d,phase,sign)
                direction = np.array([0,wrist-y,-z])/d["rod_length"]
                for name in meshes:
                    transform = np.eye(4)
                    if name == "rod":
                        transform[:3,:3] = np.column_stack(([1,0,0],direction,np.cross([1,0,0],direction)))
                        transform[:3,3] = [x_bank,y,z]
                    else:
                        transform[:3,:3] = np.diag([1,sign,sign])
                        transform[:3,3] = [x_bank,sign*d["cylinder_base"] if name == "cylinder" else wrist,0]
                    copy = meshes[name].copy(); copy.apply_transform(transform); parts.append(copy)
                    instances.append({"family":name,"pair":pair+1,"bank_sign":sign,"transform_mm":transform.tolist()})
        trimesh.util.concatenate(parts).export(output/"hypothetical-48-instance-assembly.stl")
        save(output/"assembly.json",{"classification":"hypothetical_partial_engine_48_instances","instances":instances})
        masses = {name: audits[name]["mesh_volume_mm3_hypothetical"]*config["candidate_materials"][name]["assumed_density_kg_m3"]*1e-9 for name in meshes}
        loads = []
        for rod_material in ("rod","rod_alternative"):
            rod_mass = audits["rod"]["mesh_volume_mm3_hypothetical"]*config["candidate_materials"][rod_material]["assumed_density_kg_m3"]*1e-9
            m = masses["piston"]+masses["pin"]+config["rod_reciprocating_mass_fraction"]*rod_mass
            for rpm in config["rpm_cases"]:
                accel = max(abs(acceleration(d,a,1)) for a in range(361))*1e-3*(rpm*2*math.pi/60)**2
                for pressure in config["peak_pressure_bar_cases"]:
                    gas = pressure*1e5*math.pi/4*(d["bore"]*1e-3)**2
                    loads.append({"rod_candidate":config["candidate_materials"][rod_material]["name"],"rpm":rpm,"assumed_peak_pressure_bar":pressure,
                                  "assumed_reciprocating_mass_kg":m,"gas_force_N":gas,"peak_absolute_inertia_force_N":m*accel,
                                  "independent_peak_sum_bound_N":gas+m*accel,
                                  "nominal_rod_beam_axial_stress_bound_MPa":(gas+m*accel)/(math.pi/4*d["rod_beam_diameter"]**2),
                                  "mean_piston_speed_m_s":2*d["stroke"]*1e-3*rpm/60})
        with (output/"kinematics.csv").open("x",newline="") as stream:
            writer = csv.writer(stream); writer.writerow(["angle_deg","bank_sign","crank_y_mm","crank_z_mm","wrist_y_mm"])
            for angle in range(361):
                for sign in (-1,1): writer.writerow([angle,sign,*position(d,angle,sign)])
        if (sha256(config_path) != config_hash or any(sha256(HERE/name) != value for name,value in source_hashes.items())
                or any(sha256(WITNESS/name) != value for name,value in witness_hashes.items())):
            raise ValueError("Experiment inputs changed during execution")
        result = {"classification":"hypothetical_geometry_and_reduced_order_load_screening","assumptions_sha256":config_hash,
                  "source_sha256":source_hashes,"reused_witness_sha256":witness_hashes,"levels":levels,"assembly_instances":len(instances),"motion":motion,
                  "interference":interference,
                  "assumed_material_prototype_masses_kg":masses,"partial_12_cylinder_population_mass_kg":12*sum(masses.values()),
                  "load_cases":loads,"load_scope":"constant_peak_pressure_grid_and_independent_inertia_envelope_not_combustion_or_FEA",
                  "stress_scope":"nominal_beam_axial_area_only_no_eye_contact_bending_buckling_bolts_fatigue_or_hot_allowables",
                  "nominal_piston_radial_clearance_mm":d["piston_diametral_clearance"]/2,
                  "piston_clearance_resolved_by_voxel_grid":False,
                  "release_gates":{name:False for name in ("scan_scale_verified","scan_fit_verified","complete_engine_geometry",
                                                          "functional_interfaces_verified","material_qualified","fatigue_validated",
                                                          "manufacturing_authorized","engine_start_authorized")}}
        save(output/"report.json",result)
        save(output/"status.json",{"status":"completed_hypothesis_screen_only","manufacturing_authorized":False})
        return result
    except Exception as error:
        save(output/"status.json",{"status":"failed_hypothesis_not_released","error":str(error),"manufacturing_authorized":False})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assumptions",type=Path,default=HERE/"assumptions.json")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--dotnet",required=True)
    parser.add_argument("--voxels",nargs="+",type=float,default=[1,.5])
    a = parser.parse_args()
    run(a.assumptions,a.output,a.dotnet,a.voxels)
