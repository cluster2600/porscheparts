"""Check every source facet in a declared 600 mm flat LPBF study envelope."""
import argparse
from fractions import Fraction as Q
import hashlib
import json
import math
from pathlib import Path
import resource
import signal


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True);resource.setrlimit(resource.RLIMIT_CPU,(120,130));signal.alarm(150)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    with a.mesh.open()as stream:nv,nf=map(int,stream.readline().split());vertices=np.loadtxt(stream,max_rows=nv);faces=np.loadtxt(stream,dtype=np.int64)
    if vertices.shape!=(nv,3)or faces.shape!=(nf,3):raise ValueError('Whole roster differs')
    c=math.sqrt(.5);rotation=np.array([[c,-c,0],[c,c,0],[0,0,1.]])
    rotated=vertices@rotation.T;lo=rotated.min(0);hi=rotated.max(0);translation=np.array([300-(lo[0]+hi[0])/2,300-(lo[1]+hi[1])/2,31-lo[2]])
    placed=rotated+translation;minimum=placed.min(0);maximum=placed.max(0)
    # gamma_5 covers three scalar products and two sums. The following add is
    # covered separately. These bounds refer to the exact stored matrix/shift.
    u=Q(1,2**53);gamma=5*u/(1-5*u);bounds=[]
    for axis in range(3):
        dot_bound=sum(abs(Q(float(rotation[axis,j])))*Q(float(abs(vertices[:,j]).max()))for j in range(3))
        error=gamma*dot_bound+u*((1+gamma)*dot_bound+abs(Q(float(translation[axis]))))
        bounds.append(error)
    allowed_min=[10,10,30];allowed_max=[590,590,600]
    passed=all(Q(float(minimum[i]))-bounds[i]>=allowed_min[i]and Q(float(maximum[i]))+bounds[i]<=allowed_max[i]for i in range(3))
    report=dict(status='complete_flat_part_envelope_screen_passed'if passed else'flat_part_envelope_refused',source_mesh_sha256=hashlib.sha256(a.mesh.read_bytes()).hexdigest(),worker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),vertices=nv,triangles=nf,machine_example='Nikon SLM NXG XII 600',machine_volume_mm=[600,600,600],manufacturer_source='https://nikon-slm-solutions.com/slm-systems/nxg-xii-600/',manufacturer_envelope_source='https://nikon-slm-solutions.com/newsroom/peak-productivity-slm-solutions-launches-12-laser-machine/',source_checked_date='2026-10-20',rotation_matrix=rotation.tolist(),translation_mm=translation.tolist(),placed_vertex_bounds_mm=[minimum.tolist(),maximum.tolist()],placed_size_mm=(maximum-minimum).tolist(),exact_stored_affine_rounding_bound_mm=[str(x)for x in bounds],assumed_build_plate_thickness_mm=20,assumed_minimum_support_height_mm=10,additional_placement_clearance_mm=1,assumed_XY_margin_mm=10,all_facet_containment_reason='Every triangle is a convex combination of its three vertices; guarded affine-coordinate extrema cover every vertex',supports_generated=False,machine_process_selected=False,full_layers_audited=False,geometry_adopted=False)
    (a.output/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(13,7),facecolor='#f4f7fb');fig.subplots_adjust(left=.07,right=.97,top=.76,bottom=.22,wspace=.25)
    for ax,coordinates,label in [(axes[0],[0,1],'Top view · XY'),(axes[1],[0,2],'Side view · XZ')]:
        ax.add_collection(PolyCollection(placed[faces][:,:,coordinates],facecolors='#237a69',edgecolors='none',rasterized=True));ax.set_xlim(0,600);ax.set_ylim(0,600 if coordinates==[0,1]else 120);ax.set_aspect('equal');ax.set_facecolor('#f4f7fb');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)'if coordinates==[0,1]else'Z (mm)');ax.set_title(label);ax.grid(alpha=.15)
    axes[1].axhspan(0,20,color='#aeb9c7',alpha=.7);axes[1].axhline(30,color='#bd7646',linestyle='--',lw=.8)
    fig.text(.07,.92,'993 CARRIER  /  FLAT LPBF ENVELOPE STUDY',fontsize=20,weight='bold',color='#1d334b');fig.text(.07,.84,f'600 × 600 × 600 mm reference envelope · complete projected mesh · {maximum[0]-minimum[0]:.2f} × {maximum[1]-minimum[1]:.2f} × {maximum[2]-minimum[2]:.2f} mm part',fontsize=12,color='#4c6078');fig.text(.07,.12,('The complete part fits this declared envelope.'if passed else'The placement fails the guarded envelope criterion.')+' Plate thickness and support clearance are explicit study assumptions.',fontsize=10,color='#4c6078');fig.text(.07,.065,'All source facets are projected. Support geometry, full layers and machine process files are separate preparation stages.',fontsize=10,color='#4c6078')
    image=a.output/'carrier-flat-build-envelope.png';fig.savefig(image,dpi=150,facecolor=fig.get_facecolor());plt.close(fig);signal.alarm(0)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),source_mesh_sha256=report['source_mesh_sha256'],all_source_facets_projected=nf,numpy=np.__version__,matplotlib=matplotlib.__version__),indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','placed_size_mm','placed_vertex_bounds_mm']}));return 0 if passed else 2

if __name__=='__main__':raise SystemExit(main())
