"""Render actual boundary-adjacent C3D4 stress, without nodal averaging."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--results',type=Path,required=True);p.add_argument('--assessment',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh output required')
    a.output.mkdir(parents=True)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.colors import LogNorm
    with np.load(a.mesh,allow_pickle=False)as data:v=data['vertices'];cells=data['tetrahedra'].astype(np.uint32);boundary=data['boundary'].astype(np.uint32)
    with np.load(a.results,allow_pickle=False)as data:vm=data['VM']
    report=json.loads(a.assessment.read_text())
    allfaces=np.concatenate([np.sort(cells[:,ids],axis=1)for ids in [(1,2,3),(0,3,2),(0,1,3),(0,2,1)]])
    owners=np.tile(np.arange(len(cells),dtype=np.uint32),4);order=np.lexsort(allfaces.T[::-1]);allfaces=allfaces[order];owners=owners[order];same=np.all(allfaces[1:]==allfaces[:-1],axis=1);starts=np.r_[0,np.flatnonzero(~same)+1];counts=np.diff(np.r_[starts,len(allfaces)]);idx=starts[counts==1];skin=allfaces[idx];owner=owners[idx];sorted_boundary=np.sort(boundary,axis=1);orderb=np.lexsort(sorted_boundary.T[::-1])
    if not np.array_equal(skin,sorted_boundary[orderb]):raise ValueError('Boundary ownership differs')
    owner_original=np.empty(len(boundary),dtype=np.uint32);owner_original[orderb]=owner;scalar=vm[owner_original]
    np.savez_compressed(a.output/'boundary-stress.npz',owner_cell_zero_based=owner_original,VM_MPa=scalar)
    del allfaces,owners,order,starts,counts,same,skin
    t=v[boundary];h=np.array([1.,.12,0]);h/=np.linalg.norm(h);vertical=np.cross(np.array([.2,-.6,.77]),h);vertical/=np.linalg.norm(vertical);depth=np.cross(h,vertical);xy=np.stack([t@h,t@vertical],axis=-1);order=np.argsort((t@depth).mean(axis=1));norm=LogNorm(vmin=float(vm[vm>0].min()),vmax=float(vm.max()));cmap=plt.get_cmap('inferno')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig=plt.figure(figsize=(15,7),facecolor='#f4f7fb');left=fig.add_axes([.04,.24,.58,.49]);right=fig.add_axes([.71,.23,.25,.48]);left.add_collection(PolyCollection(xy[order],facecolors=cmap(norm(scalar[order])),edgecolors='none'));left.autoscale_view();left.set_aspect('equal');left.axis('off')
    centre=np.array(report['peak_centroid_mm']);lo=centre-np.array([1.5,1.2,1.2]);hi=centre+np.array([1.5,1.2,1.2]);select=np.all((t.max(axis=1)>=lo)&(t.min(axis=1)<=hi),axis=1);local=t[select];local_order=np.argsort(local[:,:,1].mean(axis=1));projection=local[:,:,[0,2]];right.add_collection(PolyCollection(projection[local_order],facecolors=cmap(norm(scalar[select][local_order])),edgecolors='#647080',linewidths=.12));right.set_xlim(lo[0],hi[0]);right.set_ylim(lo[2],hi[2]);right.set_aspect('equal');right.set_xlabel('X (mm)');right.set_ylabel('Z (mm)');right.set_title('Root hotspot · undeformed geometry',fontsize=11,pad=14);right.plot(centre[0],centre[2],'o',mfc='none',mec='#00a1c9',ms=10,mew=1.6)
    fig.text(.04,.91,'993 CARRIER  /  FIRST COMBINED-LOAD RESULT',fontsize=20,weight='bold',color='#1d334b');fig.text(.04,.84,f"Assumed −4,000 N vertical + 850 N·m about Y · {len(cells):,} C3D4 elements",fontsize=12,color='#4c6078')
    bar=fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap=cmap),ax=left,orientation='horizontal',fraction=.035,pad=.08);bar.set_label('Boundary-adjacent element von Mises (MPa) · logarithmic scale')
    fig.text(.04,.13,f"Unconverged elastic peak: {report['integration_point_VM_max_MPa']:,.0f} MPa at X={centre[0]:.3f}, Y={centre[1]:.3f}, Z={centre[2]:.3f} mm",fontsize=11,color='#a14935');fig.text(.04,.065,'Hotspot flags a geometry/mesh investigation. No stress clipping or nodal averaging; no strength acceptance inferred.',fontsize=10,color='#4c6078')
    target=a.output/'carrier-combined-stress.png';fig.savefig(target,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    (a.output/'provenance.json').write_text(json.dumps(dict(source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.mesh,a.results,a.assessment,Path(__file__)]},figure_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),field_sha256=hashlib.sha256((a.output/'boundary-stress.npz').read_bytes()).hexdigest(),boundary_faces=len(boundary),all_surface_cells_included=True,nodal_averaging=False,color_clipping=False,zoom_bounds_mm=[lo.tolist(),hi.tolist()],numpy=np.__version__,matplotlib=matplotlib.__version__),indent=2)+'\n')

if __name__=='__main__':main()
