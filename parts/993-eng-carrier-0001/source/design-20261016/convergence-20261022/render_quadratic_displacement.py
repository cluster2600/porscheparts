"""Render complete accepted quadratic surface displacement with explicit visual amplification."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--assessment',type=Path,required=True);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=json.loads(a.assessment.read_text())
    if report['status']!='complete_linear_C3D10_results_equilibrium_and_energy_passed':raise ValueError('Accepted complete quadratic field required')
    if sha(a.results)!=report['output_sha256']or sha(a.mesh)not in report['source_sha256'].values():raise ValueError('Accepted result and geometry identity required')
    if a.output.exists():raise ValueError('Fresh output required')
    with np.load(a.mesh,allow_pickle=False)as data:v=data['vertices'].copy();boundary=data['boundary'].copy()
    with np.load(a.results,allow_pickle=False)as data:u=data['displacement'].copy()
    if u.shape!=v.shape or boundary.shape[1]!=6 or not np.isfinite(u).all():raise ValueError('Complete finite T6 surface displacement required')
    triangles=np.concatenate([boundary[:,ids]for ids in [(0,3,5),(3,1,4),(5,4,2),(3,4,5)]])
    magnitude=np.linalg.norm(u,axis=1);peak=float(magnitude.max())
    if not np.isclose(peak,report['displacement_max_mm'],rtol=1e-12,atol=1e-12):raise ValueError('Retained maximum differs')
    horizontal=np.array([1.,.12,0]);horizontal/=np.linalg.norm(horizontal);vertical=np.cross(np.array([.2,-.6,.77]),horizontal);vertical/=np.linalg.norm(vertical);depth=np.cross(horizontal,vertical)
    scale=10.;deformed=(v+scale*u)[triangles];undeformed=v[triangles];xy=np.stack([deformed@horizontal,deformed@vertical],axis=-1);original=np.stack([undeformed@horizontal,undeformed@vertical],axis=-1);order=np.argsort((deformed@depth).mean(1));scalar=magnitude[triangles].mean(1);norm=Normalize(0,peak);cmap=plt.get_cmap('viridis')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(15,6),facecolor='#f4f7fb',layout='constrained');ax.set_facecolor('#f4f7fb')
    ax.add_collection(PolyCollection(original[order],facecolors='#d0d6df',edgecolors='none'))
    ax.add_collection(PolyCollection(xy[order],facecolors=cmap(norm(scalar[order])),edgecolors='none'));ax.autoscale_view();ax.set_aspect('equal');ax.axis('off')
    fig.suptitle('993 R2 / ACCEPTED DENSE-REFERENCE DISPLACEMENT',fontsize=19,fontweight='bold',color='#1d334b')
    ax.set_title(f'{report["C3D10_elements"]:,} T10 cells · maximum displacement {peak:.6f} mm · nominal R2 mass 1.298200 kg',fontsize=12,pad=15)
    bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=ax,orientation='horizontal',fraction=.04,pad=.06);bar.set_label('Nodal displacement magnitude [mm] · surface colours average the three displayed vertex magnitudes')
    fig.supxlabel('Deformation amplified ×10 · grey: undeformed geometry · assumed −4,000 N and 850 N·m\nComplete quadratic boundary subdivided for display · equilibrium and energy passed · spatial convergence remains open',fontsize=10)
    a.output.mkdir(parents=True);target=a.output/'carrier-quadratic-displacement.png';fig.savefig(target,dpi=160);plt.close(fig)
    (a.output/'displacement-figure-provenance.json').write_text(json.dumps(dict(source_sha256={str(q):sha(q)for q in [a.mesh,a.results,a.assessment,Path(__file__)]},figure_sha256=sha(target),deformation_scale=scale,complete_boundary_faces=len(boundary),display_triangles=len(triangles),all_quadratic_boundary_nodes_included=True,displacement_max_mm=peak,stress_field_averaged=False,spatial_convergence_demonstrated=False),indent=2)+'\n')

if __name__=='__main__':main()
