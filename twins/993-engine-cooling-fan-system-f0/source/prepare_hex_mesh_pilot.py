#!/usr/bin/env python3
"""Prepare a bounded mesh-only hex-dominant pilot from an admitted original surface."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(surface,receipt,native_surface_check,output):
    info=json.loads(receipt.read_text())
    sha=hashlib.sha256(surface.read_bytes()).hexdigest()
    if (info['metres_sha256']!=sha or info.get('private_scan_used') is not False
            or info['status']!='regularized_requires_independent_surface_and_mesh_checks'):
        raise ValueError('Exact original parametric meter-surface receipt required')
    check=native_surface_check.read_text()
    if 'Surface is not self-intersecting' not in check or 'Surface is closed.' not in check:
        raise ValueError('Independent closed/intersection audit required')
    output.mkdir(parents=True,exist_ok=False)
    (output/'constant/geometry').mkdir(parents=True)
    shutil.copyfile(surface,output/'constant/geometry/rotor.stl')
    def write(name,body):
        path=output/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(f'FoamFile {{ format ascii; class dictionary; object {path.name}; }}\n'+body+'\n')
    write('system/controlDict','application snappyHexMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 0; deltaT 1; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 12; runTimeModifiable false;')
    write('system/fvSchemes','ddtSchemes { default steadyState; } gradSchemes { default Gauss linear; } divSchemes { default none; } laplacianSchemes { default Gauss linear corrected; } interpolationSchemes { default linear; } snGradSchemes { default corrected; }')
    write('system/fvSolution','solvers {}')
    write('system/blockMeshDict','''
vertices ((-.13 -.13 -.18) (.13 -.13 -.18) (.13 .13 -.18) (-.13 .13 -.18)
          (-.13 -.13 .18) (.13 -.13 .18) (.13 .13 .18) (-.13 .13 .18));
blocks (hex (0 1 2 3 4 5 6 7) (26 26 36) simpleGrading (1 1 1));
edges ();
boundary (
 inlet {type patch; faces ((0 3 2 1));}
 outlet {type patch; faces ((4 5 6 7));}
 sides {type wall; faces ((0 1 5 4) (1 2 6 5) (2 3 7 6) (3 0 4 7));}
);''')
    write('system/snappyHexMeshDict','''
castellatedMesh true; snap true; addLayers false;
geometry {
 rotor {type triSurface; file "rotor.stl";}
 duct {type cylinder; point1 (0 0 -.3); point2 (0 0 .4); radius .124;}
 nearRotor {type box; min (-.125 -.125 -.04); max (.125 .125 .04);}
}
castellatedMeshControls {
 maxLocalCells 1500000; maxGlobalCells 1500000; minRefinementCells 0;
 maxLoadUnbalance .1; nCellsBetweenLevels 3; features ();
 refinementSurfaces {
  rotor {level (4 4); patchInfo {type wall;}}
  duct {level (2 2); patchInfo {type wall;}}
 }
 resolveFeatureAngle 30;
 refinementRegions {nearRotor {mode inside; levels ((1e15 2));}}
 locationInMesh (.0521 .0123 -.1111);
 allowFreeStandingZoneFaces true;
}
snapControls {
 nSmoothPatch 5; tolerance 2; nSolveIter 100; nRelaxIter 10;
 nFeatureSnapIter 10; implicitFeatureSnap true; explicitFeatureSnap false;
 multiRegionFeatureSnap false;
}
addLayersControls {}
meshQualityControls {
 #includeEtc "caseDicts/mesh/generation/meshQualityDict"
 maxNonOrtho 65;
 maxBoundarySkewness 3.5; maxInternalSkewness 3.5;
 minVol 1e-13; minTetQuality 1e-11;
 minDeterminant .002; minFaceWeight .05; minVolRatio .01;
}
mergeTolerance 1e-6;''')
    result={'status':'prepared_mesh_only_not_accepted','source_surface_sha256':sha,
            'source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),
            'native_surface_check_sha256':hashlib.sha256(native_surface_check.read_bytes()).hexdigest(),
            'design_revision_id':info.get('design_revision_id'),'source_units':'m',
            'base_cells':[26,26,36],'rotor_surface_level':4,'maximum_cells_setting':1500000,
            'time_limit_seconds_requested':600,'container_memory_limit_GiB':6,
            'duct_radius_m_assumed':.124,'wall_layers':False,'private_scan_used':False,
            'flow_solver_prepared':False,'flow_solver_launched':False,'manufacturing_authorized':False}
    (output/'hex-preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['surface','receipt','native_surface_check','output']:p.add_argument(name,type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.surface,a.receipt,a.native_surface_check,a.output),indent=2))
