#!/usr/bin/env python3
"""Generate a private full concept assembly; reject promotion to physical release."""
import argparse
import copy
from collections import Counter
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

from engine_layout import HERE, ROOT, HYP, build, head_transform, transform
from reconstruct import check_output, check_voxels, save, sha256


def validate_imports(lock, turbo):
    if sha256(ROOT / lock["head"]["manifest"]) != lock["head"]["manifest_sha256"]:
        raise ValueError("Head delivery manifest changed")
    manifest = json.loads((ROOT / lock["head"]["manifest"]).read_text())
    published = {item["path"]: item["sha256"] for item in manifest["files"]}
    for item in lock["head"]["files"]:
        if published["cad/"+item["file"]] != item["sha256"] or sha256(ROOT/item["source"]) != item["sha256"]:
            raise ValueError("Head mesh differs from published delivery")
    if len(lock["head"]["files"]) != 13 or Counter(item["role"] for item in lock["head"]["files"]) != {"head":1,"valve":4,"seat":4,"guide":4}:
        raise ValueError("Incomplete inherited four-valve head")
    if sha256(turbo/"report.json") != lock["turbo"]["generation_sha256"]:
        raise ValueError("Turbo generation manifest changed")
    report = json.loads((turbo/"report.json").read_text())
    if (report["status"] != "concept_assembly_generated" or report["component_count"] != 39
            or report["contract_sha256"] != lock["turbo"]["contract_sha256"]
            or report["manufacturing_authorized"] is not False or report["files"] != lock["turbo"]["files"]):
        raise ValueError("Wrong or incomplete bionic turbo assembly")
    for item in lock["turbo"]["files"]:
        if Path(item["file"]).name != item["file"] or sha256(turbo/item["file"]) != item["sha256"]:
            raise ValueError("Turbo component hash mismatch")
    return report


def inspect(path, allow_exact_zero=False):
    import numpy as np
    import trimesh
    raw = trimesh.load_mesh(path,process=False)
    if not isinstance(raw,trimesh.Trimesh) or not np.isfinite(raw.vertices).all():
        raise ValueError("Expected a finite triangular mesh")
    vertices,inverse = np.unique(raw.vertices,axis=0,return_inverse=True)
    mesh = trimesh.Trimesh(vertices,inverse[raw.faces],process=False)
    removed=0
    if allow_exact_zero:
        mesh,witness=HYP.exact_zero_candidate(raw)
        removed=witness["removed_zero_cross_product_faces"]
    _,counts=np.unique(np.sort(mesh.faces,axis=1),axis=0,return_counts=True)
    components=len(mesh.split(only_watertight=False,repair=False))
    passed=bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0
                and not np.any(mesh.area_faces==0) and not np.any(counts>1) and components==1)
    report={"source_sha256":sha256(path),"triangles":len(mesh.faces),"watertight":bool(mesh.is_watertight),
            "winding_consistent":bool(mesh.is_winding_consistent),"components":components,
            "signed_volume_mm3_hypothesis":float(mesh.volume),"bounds_mm_hypothesis":mesh.bounds.tolist(),
            "removed_exact_zero_faces_only":removed,"vertex_displacement":0,"passed":passed,
            "self_intersection_checked":False}
    return mesh,report


def coverage(parts):
    # These are explicit changes of architecture, not unmodelled historical parts.
    mapping={
        "crankcase_half":["crankcase_negative","crankcase_positive"],"main_bearing":["main_bearing"],
        "crankshaft":["crankshaft"],"central_output_gear":["central_output_gear"],"output_shaft":["output_shaft"],
        "connecting_rod":["rod"],"piston":["piston"],"piston_pin":["pin"],"piston_ring":["piston_ring"],
        "individual_cylinder":["cylinder"],"individual_head":["individual_head"],
        "intake_valve":["head_component_01","head_component_04"],
        "exhaust_valve":["head_component_07","head_component_10"],
        "valve_spring":["outer_valve_spring","inner_valve_spring"],"bucket_tappet":["rocker"],
        "camshaft":["camshaft"],"cam_carrier":["rocker_carrier"],"cam_drive_gear":["cam_drive_gear"],
        "cooling_blower":["cooling_blower"],"blower_shroud":["blower_shroud"],
        "intake_trumpet":["intake_negative","intake_positive"],"injector":["injector"],"spark_plug":["spark_plug"],
        "distributor":["ignition_coil","ecu"],"pressure_oil_pump":["oil_pump_body","oil_pump_gear","oil_pump_cover","oil_pump_shaft"],
        "scavenge_oil_pump":["oil_pump_body","oil_pump_gear","oil_pump_cover","oil_pump_shaft"],
        "exhaust_primary":["exhaust_negative","exhaust_positive"],"exhaust_collector":["exhaust_negative","exhaust_positive"],
        "alternator":["alternator"],"turbocharger":["turbo_"+item for item in ("compressor_housing","turbine_housing","chra_housing")],
        "charge_plenum":["intake_negative","intake_positive"],"cooling_blower_drive_shaft":["cooling_blower_drive_shaft"],
        "cooling_blower_bevel_gear":["cooling_blower_bevel_gear"],"twelve_plunger_injection_pump":["injector","fuel_rail","ecu"],
        "injection_line":["fuel_rail"],"oil_filter":["oil_filter"],"oil_thermostat":["oil_thermostat"],"oil_cooler":["oil_cooler"],
        "cam_drive_intermediate_shaft":["cam_drive_intermediate_shaft"],"turbo_turbine_wheel":["turbo_turbine_wheel"],
        "turbo_compressor_wheel":["turbo_compressor_wheel"],"turbo_shaft":["turbo_shaft"],
        "wastegate":["turbo_wastegate_flapper","turbo_wastegate_actuator_rod"],"wastegate_bypass_pipe":["turbo_turbine_housing"]}
    f1=json.loads((ROOT/"twins/reference-917-engine/complete-engine-f1.json").read_text())
    f3=json.loads((ROOT/"twins/reference-917-engine/detail-expansion-f3.json").read_text())
    expected={item["id"] for item in f1["component_families"]+f3["families"]}
    if set(mapping)!=expected or any(set(values)-set(parts) for values in mapping.values()):
        raise ValueError("Historical family coverage missing or mapped to nonexistent geometry")
    changed={"distributor":"coil_on_plug_EFI", "twelve_plunger_injection_pump":"EFI_purchased_injectors_rails_and_ECU",
             "injection_line":"integrated_rail_no_calibrated_metering", "bucket_tappet":"rocker_concept",
             "wastegate":"inherited_internal_wastegate", "wastegate_bypass_pipe":"integrated_hot_side_passage"}
    return [{"historical_family":key,"concept_geometry":value,
             "architecture_change":changed.get(key),"manufacturing_bom_complete":False} for key,value in mapping.items()]


def add_imports(config,lock,parts,instances,xs):
    d=config["core_assumptions"]["dimensions_mm"]
    for item in lock["head"]["files"]:
        parts[item["id"]]={"id":item["id"],"import_group":"head","import":item,
                            "material_route":"head" if item["role"]=="head" else "purchase",
                            "detail_level":"inherited_four_valve_geometry_not_917_fit_verified"}
        for bank in (-1,1):
            for x in xs:
                matrix=head_transform(x-bank*d["bank_stagger"]/2,bank,config["head_deck_mm"])
                instances.append({"family":item["id"],"matrix_mm":matrix.tolist(),"bank":bank})
    for item in lock["turbo"]["files"]:
        name="turbo_"+item["id"].replace("-","_")
        parts[name]={"id":name,"import_group":"turbo","import":item,"material_route":"purchase",
                     "detail_level":"inherited_bionic_turbo_concept_unqualified"}
        for bank in (-1,1):
            matrix=transform((500,bank*330,-160))
            matrix[:3,:3]=[[0,0,1],[0,bank,0],[-bank,0,0]]
            instances.append({"family":name,"matrix_mm":matrix.tolist(),"bank":bank})
    for item in instances:
        if "matrix_mm" not in item:
            item["matrix_mm"]=transform(item["translation_mm"],item["rotation_xyz_deg"]).tolist()
    counts=Counter(item["family"] for item in instances)
    if set(counts)!=set(parts) or counts["individual_head"]!=12 or sum(counts["head_component_"+str(i).zfill(2)] for i in (1,4,7,10))!=48:
        raise ValueError("Assembly count mismatch")
    for item in parts.values(): item["quantity"]=counts[item["id"]]


def screens(config,meshes,instances):
    import numpy as np
    d=config["core_assumptions"]["dimensions_mm"]
    motion=HYP.motion_report(config["core_assumptions"])
    actual=next(row for row in motion["rod_length_sensitivity"] if row["rod_length_mm"]==d["rod_length"])
    # A witnessed ring/piston material overlap is a confirmed defect, not an AABB collision claim.
    ring_radius=(d["bore"]-.1)/2-1
    ring_probes=[[ring_radius,y,0] for y in (31,35,39)]
    overlap=bool(meshes["piston"].contains(ring_probes).any() and meshes["piston_ring"].contains([[ring_radius,0,0]])[0])
    heads=[item for item in instances if item["family"]=="individual_head"]
    head=meshes["individual_head"]
    adjacent=[]
    import trimesh
    points,_=trimesh.sample.sample_surface(head,500,seed=917)
    for bank in (-1,1):
        bank_heads=sorted((h for h in heads if h["bank"]==bank),key=lambda h:h["matrix_mm"][0][3])
        for a,b in zip(bank_heads,bank_heads[1:]):
            relative=np.linalg.inv(b["matrix_mm"])@np.asarray(a["matrix_mm"])
            in_next=head.contains(trimesh.transform_points(points,relative))
            adjacent.append({"bank":bank,"source_x_mm":a["matrix_mm"][0][3],"target_x_mm":b["matrix_mm"][0][3],
                             "material_overlap_surface_points":int(in_next.sum()),"samples":500})
    return {"core_motion":motion,"new_barrel_axial_coverage":actual,
            "cold_nominal_crown_deck_gap_mm":config["head_deck_mm"]-(d["rod_length"]+d["stroke"]/2+d["piston_pin_axis_to_crown"]),
            "ring_groove_material_overlap_witnessed":overlap,
            "adjacent_head_sampled_overlap":adjacent,
            "full_assembly_interference_checked":False,"valve_piston_swept_clearance_checked":False,
            "cam_law_or_timing_validated":False,"head_to_85mm_bore_fit_validated":False,
            "hot_clearance_validated":False,"functional_assembly_accepted":False}


def align_valve_hardware(meshes,instances):
    import numpy as np
    import trimesh
    hardware={"valve_stem_seal":1,"lower_spring_seat":7,"outer_valve_spring":9,"inner_valve_spring":9,
              "upper_spring_retainer":54,"valve_keeper_pair":54,"valve_shim":60,"rocker":64}
    heads=[item for item in instances if item["family"]=="individual_head"]
    keep=[item for item in instances if item["family"] not in hardware]
    for head in heads:
        head_matrix=np.asarray(head["matrix_mm"])
        for index in (3,6,9,12):
            guide=meshes[f"head_component_{index:02d}"]
            center=guide.center_mass
            eigenvalues,eigenvectors=np.linalg.eigh(np.cov((guide.vertices-center).T))
            axis=eigenvectors[:,np.argmax(eigenvalues)]
            if axis[2]<0:axis=-axis
            endpoint=center+axis*max((guide.vertices-center)@axis)
            local=trimesh.geometry.align_vectors([0,0,1],axis)
            for family,offset in hardware.items():
                local[:3,3]=endpoint+axis*offset
                matrix=head_matrix@local
                keep.append({"family":family,"matrix_mm":matrix.tolist(),"bank":head["bank"],
                             "placement_basis":"inherited_guide_axis_plus_assumed_installation_offsets"})
    if len(keep)!=len(instances):raise ValueError("Guide alignment lost assembly hardware")
    instances[:]=keep


def export_scene(output,meshes,instances):
    import numpy as np
    import trimesh
    scene=trimesh.Scene()
    colors={"turbo":(191,124,72,255),"head":(91,161,186,255),"bionic":(110,159,126,255)}
    for name,mesh in meshes.items():
        display=mesh.copy()
        display.apply_scale(.001)
        display.visual.face_colors=colors.get("turbo" if name.startswith("turbo") else "head" if name.startswith("head") or name=="individual_head" else "bionic",(150,160,172,255))
        scene.geometry[name]=display
    for i,item in enumerate(instances):
        matrix=np.asarray(item["matrix_mm"]).copy();matrix[:3,3]*=.001
        scene.graph.update(frame_to=f"part_{i:04d}",matrix=matrix,geometry=item["family"])
    path=output/"engine-4v-biturbo-concept.glb"
    path.write_bytes(scene.export(file_type="glb"))
    reopened=trimesh.load(path,force="scene")
    if len(reopened.graph.nodes_geometry)!=len(instances) or set(reopened.geometry)!=set(meshes):
        raise ValueError("GLB component loss")
    max_error=0.0
    for i,item in enumerate(instances):
        expected=np.asarray(item["matrix_mm"]).copy();expected[:3,3]*=.001
        matrix,name=reopened.graph[f"part_{i:04d}"]
        if name!=item["family"]:raise ValueError("GLB instance/family mismatch")
        max_error=max(max_error,float(np.abs(matrix-expected).max()))
    for name,mesh in meshes.items():
        candidate=reopened.geometry[name]
        if not np.array_equal(candidate.faces,mesh.faces):raise ValueError("GLB triangle loss")
        max_error=max(max_error,float(np.abs(candidate.vertices-mesh.vertices*.001).max()))
    if max_error>1e-6:raise ValueError("GLB metre transport error above limit")
    return {"prototypes":len(meshes),"instances":len(instances),"millimetre_to_metre_scale":.001,
            "max_coordinate_or_transform_error_m":max_error,"triangles_retained":True,"sha256":sha256(path)}


def render(output,meshes,instances):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import trimesh
    points={name:trimesh.sample.sample_surface(mesh,min(18000,max(100,len(mesh.faces)//8)),seed=917)[0]
            for name,mesh in meshes.items()}
    mechanism={"cylinder","piston","rod","pin","crankshaft","main_bearing","rod_bearing","piston_ring",
               "camshaft","rocker","rocker_carrier","individual_head","outer_valve_spring","inner_valve_spring"}
    mechanism.update(name for name in meshes if name.startswith("head_component_"))
    fig=plt.figure(figsize=(16,10),layout="constrained")
    for index,(title,hidden) in enumerate([
        ("Assemblage 4 soupapes / biturbo — hypothèses",set()),
        ("Mécanisme et culasses — carters et services masqués",set(meshes)-mechanism)]):
        ax=fig.add_subplot(2,2,index+1,projection="3d")
        buckets={}
        for item in instances:
            name=item["family"]
            if name in hidden:continue
            vertices=trimesh.transform_points(points[name],np.asarray(item["matrix_mm"]))
            color="#9f5829" if name.startswith("turbo") else "#217f9b" if name=="individual_head" else "#506762"
            buckets.setdefault(color,[]).append(vertices)
        for color,clouds in buckets.items():
            ax.scatter(*np.vstack(clouds).T,s=.55,c=color,linewidths=0,depthshade=True)
        ax.set(xlim=(-650,650),ylim=(-500,500),zlim=(-400,350),title=title)
        ax.set_box_aspect((1300,1000,750));ax.view_init(27,-58)
        ax.set_xlabel("X mm supposés");ax.set_ylabel("Y mm supposés");ax.set_zlabel("Z mm supposés")
    ax=fig.add_subplot(2,2,3,projection="3d")
    for name in ("crankcase_positive","crankshaft"):
        ax.scatter(*points[name].T,s=1.2,c="#416f50" if "case" in name else "#92672d",linewidths=0,depthshade=True)
    ax.set(xlim=(-420,420),ylim=(-110,140),zlim=(-120,150),title="Carter à nervures ramifiées et vilebrequin proposé")
    ax.set_box_aspect((840,250,270));ax.view_init(30,-50)
    ax=fig.add_subplot(2,2,4);ax.axis("off")
    ax.text(0,1,f"{len(meshes)} définitions / {len(instances)} occurrences\n12 culasses 4V — 48 soupapes héritées\n2 turbos bioniques — 39 composants chacun\n\nAlésage/course FIA : 85 / 66 mm\nCorps, sièges, guides et turbos : géométries reprises\nAutres interfaces : hypothèses explicites\n\nSurfaces représentées par points échantillonnés.\nCulasses/alésage : incompatibilité d'enveloppe détectée.\nDistribution, circuits et jeux à chaud à vérifier.\n\nAUCUNE AUTORISATION DE FABRICATION OU DÉMARRAGE",va="top",fontsize=13)
    fig.suptitle("PicoGK — moteur moderne inspiré de la 917, conception non qualifiée",fontsize=17)
    fig.savefig(output/"engine-4v-biturbo-review.png",dpi=150);plt.close(fig)


def run(output,dotnet,turbo,voxels):
    import numpy as np
    import trimesh
    output=check_output(output);voxels=check_voxels(voxels)
    config=json.loads((HERE/"design.json").read_text());lock=json.loads((HERE/"imports.json").read_text())
    f1=json.loads((ROOT/"twins/reference-917-engine/complete-engine-f1.json").read_text())
    validate_imports(lock,turbo)
    recipe,parts,instances,xs=build(config,f1);add_imports(config,lock,parts,instances,xs)
    scope=coverage(parts)
    sources=[HERE/name for name in ("Program.cs","Engine.csproj","engine_layout.py","run.py","design.json","imports.json")]
    sources += [HERE.parent/"hypothesis"/name for name in ("Program.cs","Prototype.csproj","run.py")]
    sources += [ROOT/"twins/reference-917-engine/source"/name for name in ("build_complete_engine_parts.py","build_detail_expansion_f3.py","kinematics_f2_math.py")]
    sources += [HERE.parent/"fia"/name for name in ("run.py","source-review.json")]
    pinned={str(path.relative_to(ROOT)):sha256(path) for path in sources}
    os.umask(0o077);output.mkdir(parents=True)
    save(output/"status.json",{"status":"running","manufacturing_authorized":False})
    try:
        save(output/"recipe.json",recipe);save(output/"core-assumptions.json",config["core_assumptions"])
        for name in ("design.json","imports.json"):shutil.copy2(HERE/name,output/name)
        for project,label in [(HERE/"Engine.csproj","engine"),(HERE.parent/"hypothesis/Prototype.csproj","core")]:
            with (output/(label+"-build.log")).open("x") as log:
                subprocess.run([dotnet,"build",str(project),"-c","Release","-o",str(output/(label+"-app")),
                                "-p:BaseIntermediateOutputPath="+str(output/(label+"-obj"))+os.sep],stdout=log,stderr=subprocess.STDOUT,check=True)
        meshes={};audits=[]
        for voxel in voxels:
            for label,dll,inputfile in [("core","Prototype.dll","core-assumptions.json"),("engine","Engine.dll","recipe.json")]:
                target=output/f"{label}-{voxel:g}"
                if label=="engine":
                    runtime_recipe=copy.deepcopy(recipe)
                    for item in runtime_recipe["parts"]:
                        if "source_core" in item:
                            source=output/f"core-{voxel:g}"/(item["source_core"]+"-exact-zero-only.stl")
                            item["source_mesh"]={"path":str(source),"sha256":sha256(source)}
                    inputfile=f"recipe-{voxel:g}.json"
                    save(output/inputfile,runtime_recipe)
                print(f"PicoGK {label} voxel {voxel:g}",flush=True)
                with (output/f"{label}-{voxel:g}.log").open("x") as log:
                    subprocess.run([dotnet,str(output/(label+"-app")/dll),str(output/inputfile),sha256(output/inputfile),str(voxel),str(target)],stdout=log,stderr=subprocess.STDOUT,check=True)
                receipt=json.loads((target/"receipt.json").read_text())
                records=receipt["parts"] if label=="engine" else [{"id":key,**value} for key,value in receipt["prototypes"].items()]
                expected=set(recipe_item["id"] for recipe_item in recipe["parts"]) if label=="engine" else {"cylinder","piston","rod","pin"}
                if {item["id"] for item in records}!=expected:raise ValueError("Native export set mismatch")
                rows={}
                for item in records:
                    name=item["id"];path=target/(name+".stl")
                    if sha256(path)!=item["stl_sha256"] or sha256(target/(name+".vdb"))!=item["vdb_sha256"]:
                        raise ValueError("Native output hash mismatch")
                    try:
                        mesh,report=inspect(path,allow_exact_zero=True)
                        if report["passed"]:
                            mesh.export(target/(name+"-exact-zero-only.stl"))
                            report["candidate_sha256"]=sha256(target/(name+"-exact-zero-only.stl"))
                            if voxel==min(voxels):meshes[name]=mesh
                        rows[name]=report
                    except ValueError as error:rows[name]={"passed":False,"error":str(error),"source_sha256":sha256(path)}
                save(target/"independent-audit.json",rows)
                audits.append({"voxel_mm":voxel,"group":label,"meshes":rows})
        assetdir=output/"inherited";assetdir.mkdir()
        inherited={}
        for name,part in parts.items():
            if "import" not in part:continue
            item=part["import"];source=ROOT/item["source"] if part["import_group"]=="head" else turbo/item["file"]
            path=assetdir/(name+".stl");shutil.copy2(source,path)
            mesh,report=inspect(path)
            inherited[name]=report
            if report["passed"]:meshes[name]=mesh
        save(assetdir/"independent-audit.json",inherited)
        if set(meshes)!=set(parts) or any(not row["passed"] for a in audits for row in a["meshes"].values()):
            save(output/"status.json",{"status":"rejected_component_meshes","native":audits,"inherited":inherited,"manufacturing_authorized":False})
            raise ValueError("At least one component failed independent mesh screening")
        align_valve_hardware(meshes,instances)
        for i,item in enumerate(instances):
            matrix=np.asarray(item["matrix_mm"])
            if (matrix.shape!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3],[0,0,0,1])
                    or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-12)
                    or not math.isclose(np.linalg.det(matrix[:3,:3]),1,abs_tol=1e-12)):
                raise ValueError("Invalid, mirrored or scaled instance transform")
            item["instance_id"]=f"part_{i:04d}"
        validation=screens(config,meshes,instances)
        save(output/"assembly.json",{"classification":config["classification"],"units":"mm_hypothetical", "parts":parts,"instances":instances,"historical_family_coverage":scope})
        save(output/"validation.json",validation)
        glb=export_scene(output,meshes,instances);render(output,meshes,instances)
        validate_imports(lock,turbo)
        if any(sha256(ROOT/path)!=digest for path,digest in pinned.items()):raise ValueError("Source changed during execution")
        report={"status":"concept_assembly_generated_with_unresolved_interfaces_no_release",
                "definitions":len(parts),"instances":len(instances),"new_native_definitions":67,
                "head_definitions":13,"turbo_definitions":39,"head_instances":12,"valves":48,"turbo_instances":2,
                "historical_families_accounted":len(scope),"voxel_grids_mm":voxels,"source_sha256":pinned,
                "glb_roundtrip":glb,"geometry_audits":audits,"inherited_mesh_audits":inherited,"validation":validation,
                "physical_bom_complete":False,"material_qualified":False,"manufacturing_authorized":False,"engine_start_authorized":False}
        save(output/"report.json",report);save(output/"status.json",{"status":report["status"],"manufacturing_authorized":False})
        print(json.dumps({key:report[key] for key in ("status","definitions","instances","valves","historical_families_accounted")}),flush=True)
        return report
    except Exception as error:
        save(output/"FAILED.json",{"error":str(error),"manufacturing_authorized":False});raise


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--dotnet",required=True)
    parser.add_argument("--turbo-assets",type=Path,required=True);parser.add_argument("--voxels",type=float,nargs="+",default=[1,.5])
    args=parser.parse_args()
    run(args.output,args.dotnet,args.turbo_assets,args.voxels)
