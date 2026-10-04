#!/usr/bin/env python3
"""Render actual exported BRep tessellations; no invented image geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import numpy as np


def read_binary_stl(path):
    raw=path.read_bytes()
    count=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+count*50:raise ValueError('Binary STL byte count differs')
    dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
    faces=np.frombuffer(raw,offset=84,count=count,dtype=dtype)['vertices'].astype(float)
    if not np.isfinite(faces).all():raise ValueError('Nonfinite render coordinates')
    return faces


def render(root,output,display_label=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    data=json.loads((root/'geometry-report.json').read_text());p=data['parameters']
    colors={'rotor':'#d49443','shroud':'#8ea8ad','gearcase':'#74898f','vertical_shaft':'#355d91',
            'input_shaft':'#355d91','rotor_interface_flange':'#d0b068','drive_interface_flange':'#d0b068',
            'bevel_gear_envelopes':'#b95646'}
    meshes={k:read_binary_stl(root/(k+'.stl')) for k in colors}
    fig=plt.figure(figsize=(16,7))
    for index in range(2):
        ax=fig.add_subplot(1,2,index+1,projection='3d')
        visible=['rotor'] if index==0 else list(colors)
        shown=[]
        for name in visible:
            tri=meshes[name]
            if index==1 and name in ['shroud','gearcase']:
                tri=tri[tri.mean(axis=1)[:,1]>=0]
            poly=Poly3DCollection(tri,facecolors=colors[name],linewidths=0,
                                  alpha=1,shade=True,lightsource=matplotlib.colors.LightSource(azdeg=250,altdeg=35))
            ax.add_collection3d(poly);shown.append(tri.reshape(-1,3))
        points=np.concatenate(shown);lo=points.min(axis=0);hi=points.max(axis=0)
        span=hi-lo;centre=(lo+hi)/2;extent=max(span)*.58
        ax.set_xlim(centre[0]-extent,centre[0]+extent);ax.set_ylim(centre[1]-extent,centre[1]+extent)
        ax.set_zlim(lo[2]-extent*.08,hi[2]+extent*.08)
        ax.set_box_aspect((1,1,(span[2]+extent*.16)/(2*extent)))
        ax.view_init(elev=38 if index==0 else 25,azim=-55)
        ax.set_xlabel('X [mm]');ax.set_ylabel('Y [mm]');ax.set_zlabel('Z [mm]')
        ax.zaxis.set_major_locator(MaxNLocator(4))
        ax.set_title('Analytical rotor — '+str(p['blade_count'])+' blades' if index==0 else
                     'Horizontal study assembly — display cutaway')
    fig.suptitle((display_label or p['configuration_id'])+' | assumed diameter '+str(p['diameter_mm'])+' mm',fontsize=14)
    fig.text(.5,.035,'Scale, shroud, shafts and flanges are hypotheses. Red: bevel-gear envelopes, no resolved teeth/bearings. No fit or physical qualification.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.94));fig.savefig(output,dpi=150);plt.close(fig)
    receipt={'render_source':'actual exported BRep STL tessellations','configuration_id':p['configuration_id'],
             'display_label':display_label,
             'diameter_mm_assumed':p['diameter_mm'],'source_geometry_report_sha256':hashlib.sha256((root/'geometry-report.json').read_bytes()).hexdigest(),
             'display_cutaway':'shroud and gearcase triangles with centroid Y>=0; original geometry unchanged',
             'png_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),
             'source_mesh_sha256':{k:hashlib.sha256((root/(k+'.stl')).read_bytes()).hexdigest() for k in colors}}
    output.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':'actual_geometry_rendered','configuration_id':p['configuration_id']}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('geometry',type=Path);parser.add_argument('png',type=Path)
    parser.add_argument('--display-label')
    args=parser.parse_args();render(args.geometry,args.png,args.display_label)
