#!/usr/bin/env python3
"""Render unchanged19-solid CAD assembly beside actual V2 machining-stock CAD."""
import argparse,hashlib,json,os
from pathlib import Path
import numpy as np
from screen_lpbf_geometry import triangles


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def render(root,output):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from export_s1_layout import COLORS
    geometry=root/'results/assembly/S1';report=json.loads((geometry/'geometry-report.json').read_text())
    stock=root/'results/lpbf/V2-stock-scenario';stock_report=json.loads((stock/'stock-report.json').read_text())
    if output.exists():raise ValueError('New output required')
    fig=plt.figure(figsize=(15,8));a=fig.add_subplot(121,projection='3d');b=fig.add_subplot(122,projection='3d');cloud=[];used={}
    for name,entry in report['components'].items():
        for filename,digest in entry['separate_solid_STL_sha256'].items():
            file=geometry/'geometry'/filename
            if sha(file)!=digest:raise ValueError('Assembly source STL identity')
            tri=triangles(file);cloud.append(tri.reshape(-1,3));used[str(file.relative_to(root))]=digest
            transparent=(name=='plenum_shell_envelope' or name=='V2_original_assembly' and np.ptp(tri[:,:,2])>100)
            a.add_collection3d(Poly3DCollection(tri,facecolor=COLORS[name],edgecolor='none',alpha=.24 if transparent else .95,rasterized=True))
    file=stock/'V2-stock-scenario.stl'
    if sha(file)!=stock_report['blank_stl_sha256']:raise ValueError('Stock source STL identity')
    used[str(file.relative_to(root))]=sha(file);tri=triangles(file);b.add_collection3d(Poly3DCollection(tri,facecolor=(.47,.60,.72),edgecolor=(.18,.22,.28),linewidth=.08,rasterized=True))
    for ax,points in [(a,np.concatenate(cloud)),(b,tri.reshape(-1,3))]:
        lo=points.min(axis=0);hi=points.max(axis=0);span=hi-lo
        ax.set_xlim(lo[0]-10,hi[0]+10);ax.set_ylim(lo[1]-10,hi[1]+10);ax.set_zlim(lo[2]-10,hi[2]+10)
        ax.set_box_aspect(span+20);ax.view_init(elev=24,azim=-52)
        ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.set_zlabel('Z (mm)');ax.grid(alpha=.2)
    a.set_title('Assemblage S1 — 19 solides\nCarters transparents, entraînement et supports',fontsize=12)
    b.set_title('Brut V2 — surépaisseurs d’étude\nBore radial +0,5 mm ; faces de moyeu +0,5 mm',fontsize=12)
    fig.suptitle('Ventilateur horizontal — vues de la CAO réelle à dimensions supposées',fontsize=16,y=.96)
    fig.text(.5,.09,'Diamètre 275 mm et interfaces supposés ; identité 935/993 et montage non vérifiés.',ha='center',fontsize=12)
    fig.text(.5,.055,'La transparence révèle les enveloppes. Le brut à droite est isolé, sans déplacement de ses surfaces ni champ simulé.',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.12,1,.91]);fig.savefig(output,dpi=180);plt.close(fig)
    receipt={'status':'actual_CAD_assembly_and_stock_review_render','script_sha256':sha(Path(__file__)),
             'dependency_sha256':{name:sha(Path(__file__).parent/name) for name in ['screen_lpbf_geometry.py','export_s1_layout.py']},
             'source_geometry_report_sha256':sha(geometry/'geometry-report.json'),'source_stock_report_sha256':sha(stock/'stock-report.json'),
             'source_STL_sha256':used,'PNG_sha256':sha(output),'assembly_solids':19,
             'same_native_CAD_coordinates_no_invented_geometry':True,'render_units':'mm',
             'diameter275mm_is_assumed_not_measured':True,'transparent_plenum_is_visual_only':True,
             'stock_panel_not_installed_assembly':True,'physical_validation_established':False,'manufacturing_authorized':False}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Actual S1/stock CAD delivery render written')


if __name__=='__main__':
    os.nice(15);cli=argparse.ArgumentParser(description=__doc__);cli.add_argument('root',type=Path);cli.add_argument('output',type=Path)
    a=cli.parse_args();render(a.root,a.output)
