#!/usr/bin/env python3
"""Plot actual undeformed CalculiX nodal fields with full-range color scales."""
import argparse
import hashlib
import json
from pathlib import Path


def render(summary,output):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    report=json.loads(summary.read_text());field_path=summary.with_suffix('.npz');fields=np.load(field_path)
    xyz=fields['xyz_mm'];stress=fields['von_mises_nodal_MPa'];u=np.linalg.norm(fields['displacement_mm'],axis=1)
    fig=plt.figure(figsize=(14,6))
    for index,(values,title,label) in enumerate([(stress,'Nodally averaged von Mises stress','MPa'),(u,'Displacement magnitude','mm')]):
        ax=fig.add_subplot(1,2,index+1,projection='3d')
        dots=ax.scatter(*xyz.T,c=values,cmap='turbo',s=.5,vmin=0,vmax=float(values.max()),rasterized=True)
        ax.set_box_aspect((1,1,.23));ax.view_init(32,-55);ax.set_xlabel('X [mm]');ax.set_ylabel('Y [mm]');ax.set_zlabel('Z [mm]')
        ax.zaxis.set_major_locator(MaxNLocator(3))
        ax.set_title(title+' | maximum '+format(float(values.max()),'.4g')+' '+label);fig.colorbar(dots,ax=ax,shrink=.65,label=label)
    fig.suptitle(report['configuration_id']+' | '+str(report['rpm_assumed'])+' rpm assumed | '+str(report['mesh']['volume_elements'])+' C3D10')
    fig.text(.5,.025,'Actual solver nodes on undeformed coordinates; all nodes and full maxima retained. Assumed aluminium and fixed bore. No safe RPM or fatigue qualification.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.06,1,.92));fig.savefig(output,dpi=140);plt.close(fig)
    receipt={'status':'actual_FEM_nodal_fields_rendered','all_nodes_displayed':len(xyz),'deformation_magnification':0,
             'source_summary_sha256':hashlib.sha256(summary.read_bytes()).hexdigest(),'source_fields_sha256':hashlib.sha256(field_path.read_bytes()).hexdigest(),
             'full_color_maxima_retained':True,'png_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('summary',type=Path);p.add_argument('png',type=Path)
    a=p.parse_args();print(json.dumps(render(a.summary,a.png)))
