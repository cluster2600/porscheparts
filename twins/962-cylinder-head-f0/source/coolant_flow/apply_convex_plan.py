"""Apply a hash-bound face selection without the native remover's boundary simplification."""
import argparse
import json
from pathlib import Path
import re
import shutil

from merge_flagged_cells import merged_connectivity,read_list,sha


def apply(case,selection,output):
    if output.exists():raise ValueError('Output must be new')
    plan=json.loads((selection/'selection-plan.json').read_text());mesh=case/'constant/polyMesh'
    for name,digest in plan['mesh_hashes'].items():
        if sha(mesh/name)!=digest:raise ValueError('Plan mesh binding changed: '+name)
    if sha(selection/'convexMerges')!=plan['selection_sha256']:raise ValueError('Face selection changed')
    chosen=set(map(int,read_list(selection/'convexMerges')))
    faces=read_list(mesh/'faces');owners=list(map(int,read_list(mesh/'owner')))
    neighbours=list(map(int,read_list(mesh/'neighbour')))
    new_faces,new_owner,new_neighbour,count=merged_connectivity(faces,owners,neighbours,chosen)
    if new_faces[len(new_neighbour):]!=faces[len(neighbours):]:raise ValueError('Oriented boundary faces changed')
    for name in ('0','constant','system'):shutil.copytree(case/name,output/name)
    for name in ('case-report.json','accept_mesh.py'):shutil.copy2(case/name,output/name)
    target=output/'constant/polyMesh'
    def write(name,kind,rows):
        (target/name).write_text('FoamFile { format ascii; class '+kind+'; object '+name+'; }\n'+str(len(rows))+'\n(\n'+'\n'.join(map(str,rows))+'\n)\n')
    write('faces','faceList',new_faces);write('owner','labelList',new_owner);write('neighbour','labelList',new_neighbour)
    write('cellZones','regIOobject',[])
    if (target/'sets').exists():shutil.rmtree(target/'sets')
    removed=len(neighbours)-len(new_neighbour)
    (target/'boundary').write_text(re.sub(r'(startFace\s+)(\d+)',lambda m:m[1]+str(int(m[2])-removed),(mesh/'boundary').read_text()))
    report=dict(status='exact_boundary_convex_plan_requires_checkMesh',source_sha256=sha(Path(__file__)),
        connectivity_source_sha256=sha(Path(__file__).with_name('merge_flagged_cells.py')),
        plan_sha256=sha(selection/'selection-plan.json'),cells=count,removed_internal_faces=removed,
        points_unchanged=sha(target/'points')==sha(mesh/'points'),oriented_boundary_faces_unchanged=True,
        mesh_hashes={p.name:sha(p) for p in target.iterdir() if p.is_file()},
        openfoam_mesh_accepted=False,manufacturing_authorized=False)
    (output/'convex-plan-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('case','selection','output'):p.add_argument(name,type=Path)
    a=p.parse_args();apply(a.case.resolve(),a.selection.resolve(),a.output.resolve())
