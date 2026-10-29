"""Show actual retained material in four finite internal regions, with cutaways."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    import manifold3d as mf
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    p=argparse.ArgumentParser(__doc__);p.add_argument('--envelope-directory',type=Path,required=True);p.add_argument('--networks',type=Path,nargs=4,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists()
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    er=json.loads((a.envelope_directory/'assessment.json').read_text());archive=a.envelope_directory/'envelopes.npz'
    assert sha(archive)==er['output_sha256']['envelopes.npz']
    z=np.load(archive);inputs={str(archive):sha(archive)};observations=[]
    fig=plt.figure(figsize=(12.5,8.5),layout='constrained',facecolor='#f4f1e9');vstart=fstart=0
    for rank,directory in enumerate(a.networks):
        r=json.loads((directory/'assessment.json').read_text());assert r['rank']==rank and r['status']=='dominant_void_network_per_analytic_sign_retained'
        assert not r['carrier_geometry_changed'] and len(r['selected'])==2
        c=er['components'][rank];v=np.array(z['vertices'][vstart:vstart+c['vertices']]);f=np.array(z['triangles'][fstart:fstart+c['triangles']]-vstart,dtype=np.uint64)
        core=mf.Manifold(mf.Mesh64(v,f));networks=[]
        for selected in r['selected']:
            path=directory/selected['file'];assert sha(path)==selected['sha256'];inputs[str(path)]=sha(path)
            n=np.load(path);networks.append(mf.Manifold(mf.Mesh64(np.array(n['vertices']),np.array(n['triangles'],dtype=np.uint64))))
        void=mf.Manifold.batch_boolean(networks,mf.OpType.Add);material=core-void
        assert material.status()==mf.Error.NoError and abs(material.volume()-(core.volume()-r['retained_void_volume_mm3']))/core.volume()<=1e-10
        shells=[s.volume()for s in material.decompose()];positive=sum(x>0 for x in shells);negative=sum(x<0 for x in shells)
        assert positive==1 and negative==2
        low=v.min(0);high=v.max(0);centre=(low+high)/2;size=high-low+2;size[2]=centre[2]-low[2]+1
        box=mf.Manifold.cube(tuple(size)).translate(tuple(low-1))
        display=mf.Manifold.batch_boolean([material,box],mf.OpType.Intersect).as_original().simplify(.02)
        assert display.status()==mf.Error.NoError and display.volume()>0
        mesh=display.to_mesh64();points=np.array(mesh.vert_properties)[:,:3];triangles=np.array(mesh.tri_verts);t=points[triangles]
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-30)
        light=.42+.58*abs(normal@np.array([.3,-.4,.866]));color=np.array([.12,.44,.43])[None,:]*light[:,None]+.12
        ax=fig.add_subplot(2,2,rank+1,projection='3d',facecolor='#f4f1e9');ax.add_collection3d(Poly3DCollection(t,facecolors=color,edgecolors='none',rasterized=True))
        radius=max(high-low)*.55
        ax.set(xlim=(centre[0]-radius,centre[0]+radius),ylim=(centre[1]-radius,centre[1]+radius),zlim=(centre[2]-radius,centre[2]+radius));ax.set_box_aspect((1,1,1),zoom=1.65);ax.view_init(34,-53);ax.set_axis_off()
        ax.set_title(f"Region {rank+1} / retained material {100*r['finite_retained_solid_fraction']:.2f}%\nTwo void networks retained / {r['discarded_void_pockets']} small pockets filled",fontsize=10,loc='left',color='#203b3b')
        observations.append(dict(rank=rank,material_volume_mm3=material.volume(),positive_material_shells=positive,negative_void_shells=negative,display_triangles=len(triangles),cut_plane_z_mm=float(centre[2]),display_simplification_mm=.02))
        inputs[str(directory/'assessment.json')]=sha(directory/'assessment.json');vstart+=c['vertices'];fstart+=c['triangles']
    fig.suptitle('FINITE GYROID / INTERNAL MATERIAL CUTAWAYS',fontsize=17,fontweight='bold',color='#203b3b')
    fig.supxlabel('Actual generated geometry / 6 mm pitch / 0.125 mm sampling\nInternal regions only; the full carrier and powder-escape ports are not generated here.\nDisplay clipped at mid-height and simplified by 0.02 mm; numerical meshes are unchanged.',fontsize=10,color='#203b3b')
    a.output.mkdir();path=a.output/'finite-gyroid-cutaways.png';fig.savefig(path,dpi=160);plt.close(fig)
    (a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_sha256=sha(path),input_sha256=inputs,source_sha256={str(Path(__file__)):sha(Path(__file__))},regions=observations,carrier_geometry_changed=False,powder_escape_demonstrated=False,manufacturing_authorized=False),indent=2)+'\n')


if __name__=='__main__':main()
