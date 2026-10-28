"""Render actual quadratic research-cell boundaries and an element cutaway."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();r=json.loads((a.mesh/'assessment.json').read_text());assert r['status']=='explicit_periodic_T10_research_mesh_audited';z=np.load(a.mesh/'transport.npz');points=z['points'];cells=z['cells']
    import pyvista as pv
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    grid=pv.UnstructuredGrid({pv.CellType.QUADRATIC_TETRA:cells},points);full=grid.extract_surface(nonlinear_subdivision=1).triangulate();keep=points[cells[:,:4],0].mean(1)<0;cut=grid.extract_cells(keep).extract_surface(nonlinear_subdivision=1).triangulate()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1'});fig=plt.figure(figsize=(12,6.5),layout='constrained');counts=[]
    for i,(surface,title)in enumerate([(full,'Explicit solid / same fixed level set'),(cut,'Quadratic volume mesh / element cutaway')]):
        ax=fig.add_subplot(1,2,i+1,projection='3d');faces=surface.faces.reshape(-1,4);assert np.all(faces[:,0]==3);tri=surface.points[faces[:,1:]];counts.append(len(tri));norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-30);light=.4+.6*abs(norm@np.array([.3,-.4,.866]));base=np.array([.22,.47,.46]);colors=base[None,:]*light[:,None]+.15
        poly=Poly3DCollection(tri,facecolors=colors,edgecolors='#173b39'if i else 'none',linewidths=.08 if i else 0,rasterized=True);ax.add_collection3d(poly)
        for axis in range(3):
            other=[j for j in range(3)if j!=axis]
            for u in [-.5,.5]:
                for v in [-.5,.5]:
                    edge=np.zeros((2,3));edge[:,axis]=[-.5,.5];edge[:,other]=[u,v];ax.plot(*edge.T,color='#79848a',linewidth=.5,alpha=.5)
        ax.set(xlim=(-.55,.55),ylim=(-.55,.55),zlim=(-.55,.55));ax.set_box_aspect((1,1,1));ax.view_init(24,-52);ax.set_axis_off();ax.set_title(title,loc='left',fontweight='bold',pad=0)
    fig.suptitle('993 CARRIER / EXPLICIT PERIODIC CELL RESEARCH',fontweight='bold',fontsize=17);fig.supxlabel(f"1 mm reference cube / {len(cells):,} T10 elements / {len(points):,} physical nodes\nActual generated geometry and mesh. No new carrier geometry, strength or printability claim.",fontsize=10)
    a.output.mkdir();image=a.output/'explicit-periodic-cell.png';fig.savefig(image,dpi=160);plt.close(fig);sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();(a.output/'figure-provenance.json').write_text(json.dumps(dict(figure_kind='actual_numerical_research_geometry',figure_sha256=sha(image),full_boundary_display_triangles=counts[0],cutaway_display_triangles=counts[1],all_quadratic_boundary_nodes_included=True,element_cutaway=True,carrier_geometry_changed=False,source_sha256={str(f):sha(f)for f in [Path(__file__),a.mesh/'transport.npz',a.mesh/'assessment.json']}),indent=2)+'\n')


if __name__=='__main__':main()
