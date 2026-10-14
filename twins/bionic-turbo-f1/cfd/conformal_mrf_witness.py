#!/usr/bin/env python3
"""Test a faceted radial MRF interface with rotation tangent to every interface face."""
import json
import math
from pathlib import Path
import sys

import static_mrf_witness as witness
from prepare_case import header, sha


def mesh_text():
    sectors=32
    radii=(.01,.02,.04)
    vertices=[(r*math.cos(2*math.pi*i/sectors),r*math.sin(2*math.pi*i/sectors),z)
              for z in (-.04,.04) for r in radii for i in range(sectors)]
    blocks=[];walls=[]
    for shell,nr in ((0,5),(1,10)):
        for i in range(sectors):
            j=(i+1)%sectors
            bottom=[shell*sectors+i,(shell+1)*sectors+i,(shell+1)*sectors+j,shell*sectors+j]
            v=bottom+[k+3*sectors for k in bottom]
            blocks.append('hex ('+' '.join(map(str,v))+f') ({nr} 1 20) simpleGrading (1 1 1)')
            walls.extend(([v[k] for k in (0,3,2,1)],[v[k] for k in (4,5,6,7)]))
            walls.append([v[k] for k in ((0,4,7,3) if shell==0 else (1,2,6,5))])
    assert len(vertices)==192 and len(blocks)==64 and len(walls)==192
    vec=lambda values:'('+' '.join(f'{v:.15g}' for v in values)+')'
    return header('blockMeshDict')+'vertices ('+' '.join(map(vec,vertices))+');\nblocks ('+'\n'.join(blocks)+');\nedges ();\nboundary (walls {type wall; faces ('+' '.join(map(vec,walls))+');});\n'


def prepare(parent,case):
    manifest=witness.prepare(parent,case,10471.975511966)
    (case/'system/blockMeshDict').write_text(mesh_text())
    manifest['file_sha256']['system/blockMeshDict']=sha(case/'system/blockMeshDict')
    manifest['aligned_radial_interface']={'source_sha256':sha(Path(__file__)),'sectors':32,'radii_m':[.01,.02,.04],
        'cells':9600,'expected_rotating_cells':3200,'expected_interface_faces':640,
        'reason':'Undivided angular faces with paired axial vertices put each face centroid on its radial normal; rotation has zero normal component.',
        'limitation':'Small annular stationary-gas witness, not the turbo geometry or a qualified turbo mesh.'}
    (case/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    parent,case=map(Path,sys.argv[1:])
    report=witness.run(case,prepare(parent,case))
    if report['native_exit_code']==0:
        assert 'cellZoneSet rotorZone now size 3200' in (case/'log.topoSet').read_text()
    print(json.dumps(report),flush=True)
