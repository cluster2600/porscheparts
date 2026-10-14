#!/usr/bin/env python3
"""Prepare a fixed-flow, free-discharge carenage pilot; no rotating fan or engine heat model."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pyvista as pv
import trimesh

STUDY = Path(__file__).resolve().parents[1]


def port_labels(centres, card):
    g=card["geometry"]
    labels=np.full(len(centres),"walls",dtype=object)
    labels[np.abs(centres[:,1]-g["fan_rear_y_mm"])<.01]="inlet"
    for side,x in (("left",-g["outlet_x_mm"]),("right",g["outlet_x_mm"])):
        for i,y in enumerate(g["outlet_y_mm"]):
            at_port=(np.abs(centres[:,2]-g["outlet_z_mm"])<.01)&(np.hypot(centres[:,0]-x,centres[:,1]-y)<g["outlet_radius_mm"]+3)
            labels[at_port]=f"{side}{i+1}"
    return labels


def run(native, output, flow):
    if not np.isfinite(flow) or flow<=0: raise ValueError("Positive finite flow required")
    if output.exists(): raise FileExistsError(output)
    card=json.loads((STUDY/"study.json").read_text())
    original=trimesh.load_mesh(native,process=True)
    original.update_faces(original.nondegenerate_faces() & original.unique_faces())
    original.remove_unreferenced_vertices()
    if not original.is_watertight or original.body_count!=1: raise ValueError("Closed single fluid domain required")
    poly=pv.PolyData(original.vertices,np.column_stack((np.full(len(original.faces),3),original.faces)))
    small=poly.decimate_pro(.90,preserve_topology=True)
    mesh=trimesh.Trimesh(small.points,small.faces.reshape(-1,4)[:,1:],process=True)
    error=abs(mesh.volume/original.volume-1)
    if not mesh.is_watertight or mesh.body_count!=1 or error>.005: raise ValueError("Analysis surface lost topology or volume")
    labels=port_labels(mesh.triangles_center,card)
    names=["walls","inlet","left1","left2","left3","right1","right2","right3"]
    if set(labels)!=set(names): raise ValueError("Missing fluid port")
    for name in ("system","constant/triSurface","0"):(output/name).mkdir(parents=True)
    with (output/"constant/triSurface/duct.stl").open("w") as stream:
        for name in names:
            stream.write(f"solid {name}\n")
            for triangle,normal in zip(mesh.triangles[labels==name]/1000,mesh.face_normals[labels==name]):
                stream.write("facet normal "+" ".join(f"{v:.9g}" for v in normal)+"\nouter loop\n")
                for vertex in triangle:stream.write("vertex "+" ".join(f"{v:.9g}" for v in vertex)+"\n")
                stream.write("endloop\nendfacet\n")
            stream.write(f"endsolid {name}\n")
    def write(path,body,cls="dictionary"):
        obj=Path(path).name
        (output/path).write_text(f"FoamFile {{version 2.0; format ascii; class {cls}; object {obj};}}\n"+body+"\n")
    write("system/blockMeshDict",'''scale 1;
vertices ((-.29 -.21 .005)(.29 -.21 .005)(.29 .32 .005)(-.29 .32 .005)
          (-.29 -.21 .325)(.29 -.21 .325)(.29 .32 .325)(-.29 .32 .325));
blocks (hex (0 1 2 3 4 5 6 7) (116 106 64) simpleGrading (1 1 1));
edges (); boundary (outer {type wall; faces ((0 4 7 3)(1 2 6 5)(0 1 5 4)(3 7 6 2)(0 3 2 1)(4 5 6 7));});''')
    regions="\n".join(f"{n} {{ name {n}; }}" for n in names)
    write("system/snappyHexMeshDict",'''castellatedMesh true; snap true; addLayers false;
geometry {duct.stl {type triSurfaceMesh; name duct; regions {'''+regions+'''}}}
castellatedMeshControls {
 maxLocalCells 1000000; maxGlobalCells 1500000; minRefinementCells 0; maxLoadUnbalance .1;
 nCellsBetweenLevels 3; features (); refinementSurfaces {duct {level (0 0); patchInfo {type wall;}}}
 resolveFeatureAngle 30; refinementRegions {}; locationInMesh (.15 .12 .15); allowFreeStandingZoneFaces true;
}
snapControls {nSmoothPatch 3; tolerance 2; nSolveIter 30; nRelaxIter 5; nFeatureSnapIter 0;}
addLayersControls {}
meshQualityControls {
 maxNonOrtho 65; maxBoundarySkewness 20; maxInternalSkewness 4; maxConcave 80;
 minVol 1e-13; minTetQuality 1e-15; minArea -1; minTwist .02; minDeterminant .001;
 minFaceWeight .05; minVolRatio .01; minTriangleTwist -1; nSmoothScale 4; errorReduction .75;
}
mergeTolerance 1e-6;''')
    functions="\n".join(f'''{n} {{type surfaceFieldValue; libs ("libfieldFunctionObjects.so");
writeControl timeStep; writeInterval 1; regionType patch; name {n}; operation sum; fields (phi); writeFields false;}}''' for n in names[1:])
    write("system/controlDict",'''application simpleFoam; startFrom startTime; startTime 0; stopAt endTime;
endTime 600; deltaT 1; writeControl timeStep; writeInterval 200; purgeWrite 1;
writeFormat ascii; writePrecision 10; runTimeModifiable false;
functions {'''+functions+'''}''')
    write("system/fvSchemes",'''ddtSchemes {default steadyState;}
gradSchemes {default cellLimited Gauss linear 1;}
divSchemes {default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind;
div(phi,omega) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear;}
laplacianSchemes {default Gauss linear limited .5;} interpolationSchemes {default linear;}
snGradSchemes {default limited .5;} wallDist {method meshWave;}''')
    write("system/fvSolution",'''solvers {p {solver GAMG; tolerance 1e-7; relTol .05; smoother GaussSeidel;}
"(U|k|omega)" {solver smoothSolver; smoother symGaussSeidel; tolerance 1e-8; relTol .05;}}
SIMPLE {nNonOrthogonalCorrectors 1; consistent yes;}
relaxationFactors {fields {p .25;} equations {U .5; k .5; omega .5;}}''')
    write("system/decomposeParDict","numberOfSubdomains 4; method scotch;")
    write("constant/transportProperties","transportModel Newtonian; nu [0 2 -1 0 0 0 0] 1.5e-5;")
    write("constant/turbulenceProperties","simulationType RAS; RAS {RASModel kOmegaSST; turbulence on; printCoeffs on;}")
    write("0/U",f'''dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0);
boundaryField {{inlet {{type flowRateInletVelocity; volumetricFlowRate constant {flow}; value uniform (0 60 0);}}
"(left.*|right.*)" {{type pressureInletOutletVelocity; value uniform (0 0 0);}}
walls {{type noSlip;}} outer {{type noSlip;}}}}''',"volVectorField")
    write("0/p",'''dimensions [0 2 -2 0 0 0 0]; internalField uniform 0;
boundaryField {inlet {type zeroGradient;} "(left.*|right.*)" {type fixedValue; value uniform 0;}
walls {type zeroGradient;} outer {type zeroGradient;}}''',"volScalarField")
    for name,dim,val,wall in (("k","[0 2 -2 0 0 0 0]",1.5,"kqRWallFunction"),("omega","[0 0 -1 0 0 0 0]",100,"omegaWallFunction"),("nut","[0 2 -1 0 0 0 0]",0,"nutkWallFunction")):
        inlet="calculated" if name=="nut" else "fixedValue"
        outlet="calculated" if name=="nut" else "inletOutlet"
        extra="" if name=="nut" else f"inletValue uniform {val};"
        write("0/"+name,f'''dimensions {dim}; internalField uniform {val}; boundaryField {{
inlet {{type {inlet}; value uniform {val};}} "(left.*|right.*)" {{type {outlet}; {extra} value uniform {val};}}
"(walls|outer)" {{type {wall}; value uniform {val};}}}}''',"volScalarField")
    receipt={"status":"prepared_not_solved","scope":"stationary_delivery_duct_fixed_flow_free_discharge",
        "fan_resolved":False,"intercooler_resolved":False,"engine_heat_transfer_resolved":False,
        "physical_validation":False,"flow_m3_s":flow,"source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "study_sha256":hashlib.sha256((STUDY/"study.json").read_bytes()).hexdigest(),
        "native_surface_sha256":hashlib.sha256(native.read_bytes()).hexdigest(),"surface_volume_relative_error":error,
        "triangles":len(mesh.faces),"patch_triangles":{n:int((labels==n).sum()) for n in names}}
    (output/"preparation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--native",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    p.add_argument("--flow",type=float,required=True)
    a=p.parse_args();run(a.native,a.output,a.flow)
