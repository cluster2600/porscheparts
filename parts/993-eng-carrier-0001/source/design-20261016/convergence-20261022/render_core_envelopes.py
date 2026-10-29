"""Render the actual checked inner-envelope meshes, without a carrier-shape claim."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    r=json.loads((a.directory/'assessment.json').read_text());assert r['status']=='four_largest_core_envelopes_conservatively_eroded_and_transfer_checked'
    assert all(c['native_components']==1 and c['exact_oriented_triangle_roundtrip']for c in r['components'])
    assert sha(a.directory/'envelopes.npz')==r['output_sha256']['envelopes.npz']
    z=np.load(a.directory/'envelopes.npz');vertices=z['vertices'];triangles=z['triangles']
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig=plt.figure(figsize=(12,8),layout='constrained');vstart=fstart=0
    for i,c in enumerate(r['components']):
        v=vertices[vstart:vstart+c['vertices']];f=triangles[fstart:fstart+c['triangles']]-vstart;t=v[f]
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-30)
        light=.45+.55*abs(normal@np.array([.3,-.4,.866]));color=np.array([.22,.47,.46])[None,:]*light[:,None]+.15
        ax=fig.add_subplot(2,2,i+1,projection='3d');ax.add_collection3d(Poly3DCollection(t,facecolors=color,edgecolors='#244947',linewidths=.035,rasterized=True))
        low=v.min(0);high=v.max(0);centre=(low+high)/2;span=high-low;radius=max(span)*.55
        ax.set(xlim=(centre[0]-radius,centre[0]+radius),ylim=(centre[1]-radius,centre[1]+radius),zlim=(centre[2]-radius,centre[2]+radius));ax.set_box_aspect((1,1,1));ax.view_init(24,-52);ax.set_axis_off()
        ax.set_title(f"Region {i+1} / {c['volume_mm3']:.2f} mm³\n1 connected closed body / exact oriented-triangle roundtrip",fontsize=10,loc='left')
        vstart+=c['vertices'];fstart+=c['triangles']
    assert vstart==len(vertices) and fstart==len(triangles)
    fig.suptitle('993 CARRIER / CONSERVATIVE INNER ENVELOPES',fontsize=17,fontweight='bold')
    fig.supxlabel('Actual mesh geometry / 0.10 mm inward erosion / tiny disconnected remnants discarded\nThese are internal region envelopes. No lattice or modified carrier is shown.',fontsize=10)
    a.output.mkdir();image=a.output/'core-envelopes.png';fig.savefig(image,dpi=160);plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(image),source_sha256={str(f):sha(f)for f in [Path(__file__),a.directory/'assessment.json',a.directory/'envelopes.npz']},carrier_geometry_changed=False),indent=2)+'\n')


if __name__=='__main__':main()
