#!/usr/bin/env python3
"""Audit native PicoGK parts and publish a compact, explicitly provisional assembly."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
import pyvista as pv
import trimesh

ROOT=Path(__file__).resolve().parents[3]
STUDY=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(native,output):
    if output.exists(): raise FileExistsError(output)
    card=json.loads((STUDY/"study.json").read_text())
    output.mkdir(parents=True)
    (output/"native").mkdir()
    scene=trimesh.Scene(); parts=[]; drawn=[]
    for path in sorted(native.glob("*.stl")):
        mesh=trimesh.load_mesh(path,process=True)
        count=len(mesh.faces)
        volume_before=mesh.volume
        mesh.update_faces(mesh.nondegenerate_faces() & mesh.unique_faces())
        mesh.remove_unreferenced_vertices()
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.body_count!=1 or mesh.volume<=0:
            raise ValueError("Native topology rejected: "+path.name)
        if abs(mesh.volume/volume_before-1)>1e-7: raise ValueError("Cleaning changed volume")
        data=mesh.export(file_type="stl")
        (output/"native"/(path.name+".gz")).write_bytes(gzip.compress(data,mtime=0))
        name=path.stem
        record={"name":name,"input_sha256":sha(path),"cleaned_stl_sha256":hashlib.sha256(data).hexdigest(),
                "removed_degenerate_or_duplicate_faces":count-len(mesh.faces),"watertight":True,"bodies":1,
                "volume_mm3":float(mesh.volume),"bounds_mm":mesh.bounds.tolist()}
        parts.append(record)
        if name=="delivery-fluid-domain" or name in ("rotor-twist--4","rotor-twist-4"): continue
        poly=pv.PolyData(mesh.vertices,np.column_stack((np.full(len(mesh.faces),3),mesh.faces)))
        poly=poly.decimate_pro(max(0,1-16000/len(mesh.faces)),preserve_topology=True)
        visual=trimesh.Trimesh(poly.points,poly.faces.reshape(-1,4)[:,1:],process=True)
        if name.startswith("rotor"):
            transform=np.array([[1,0,0,0],[0,0,1,card["geometry"]["fan_front_y_mm"]],
                                [0,-1,0,card["geometry"]["fan_centre_z_mm"]],[0,0,0,1]],float)
            visual.apply_transform(transform)
            record["assembly_transform"]=transform.tolist()
        color=([45,144,214,80] if "shroud" in name else [245,147,44,255] if "rotor" in name
               else [115,125,133,255] if "alternator" in name else [108,179,155,180] if "engine-envelope" in name
               else [195,205,216,230] if "core" in name else [75,112,158,220])
        visual.visual=trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(baseColorFactor=color,metallicFactor=.15,roughnessFactor=.6,alphaMode="BLEND"))
        metric=visual.copy();metric.apply_scale(.001)
        scene.add_geometry(metric,node_name=name,geom_name=name)
        drawn.append((name,visual,color))
    (output/"assembly.glb").write_bytes(scene.export(file_type="glb"))
    fig=plt.figure(figsize=(15,8))
    for index,(azimuth,elevation) in enumerate(((-65,25),(105,20))):
        ax=fig.add_subplot(1,2,index+1,projection="3d")
        for name,mesh,color in drawn:
            c=np.array(color)/255
            if "shroud" in name:c[3]=.12
            ax.add_collection3d(Poly3DCollection(mesh.triangles,facecolors=[c],edgecolors="none",rasterized=True))
        top=card["geometry"]["core_bottom_z_mm"]+card["geometry"]["core_thickness_mm"]+20
        ax.set(xlim=(-440,440),ylim=(-400,330),zlim=(-90,top),xlabel="X lateral (mm)",ylabel="Y enginewards (mm)",zlabel="Z up (mm)")
        ax.set_box_aspect((880,730,top+90));ax.view_init(elevation,azimuth)
        ax.set_title("Rear intake side" if index==0 else "Six engine cooling exits")
    fig.suptitle("PicoGK installed cooling concept — horizontal air-to-air intercooler\nHypothetical packaging; engine and alternator shown as envelopes",fontsize=15)
    fig.text(.5,.04,"Blue: air ducts | Orange: rotor | Grey: core and alternator | Green: six engine envelopes\nCore 620 × 450 × 60 mm is a design assumption; no measured wing clearance or functional acceptance.",ha="center",fontsize=11)
    fig.subplots_adjust(left=0,right=.99,bottom=.15,top=.87,wspace=.05)
    fig.savefig(output/"assembly.png",dpi=130);plt.close(fig)
    sources=[STUDY/"study.json",STUDY/"interface-contract.json",Path(__file__),STUDY/"source/Program.cs",STUDY/"source/Cooling.csproj",
             ROOT/card["rotor_parameters"],ROOT/"parts/picogk-catalog/rotating/AxialFans.cs",ROOT/"parts/picogk-catalog/rotating/RotKit.cs",ROOT/"parts/picogk-catalog/common/Sdf.cs"]
    manifest={"status":"geometry_audited_packaging_hypothesis_only","kernel_generation":json.loads((native/"generation.json").read_text()),
              "manufacturing_authorized":False,"measured_fit":False,"cfd_ready":False,
              "visual_meshes":"Decimated for review only; GLB units metres; native STL units mm.",
              "source_hashes":{str(p.relative_to(ROOT)):sha(p) for p in sources},"parts":parts,
              "output_hashes":{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob("*")) if p.is_file()}}
    (output/"geometry-review.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"parts":len(parts),"native_topology":"all single closed solids after degenerate-face cleanup"}))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--native",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();run(a.native,a.output)
