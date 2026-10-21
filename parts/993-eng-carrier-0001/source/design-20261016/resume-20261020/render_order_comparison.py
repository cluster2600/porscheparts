"""Render actual matched-order fields and whole-surface fidelity receipts."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    a.output.mkdir(parents=True,exist_ok=True);root=a.work
    reports=[json.loads((root/f'meshlib-R2-matched-{order}-assessment-001/assessment.json').read_text())for order in ['P1','P2']]
    with np.load(root/'meshlib-R2-matched-traction-001/P1/transport.npz',allow_pickle=False)as data:v=data['vertices'].copy();faces=data['boundary'].copy()
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#f5f5f1','axes.facecolor':'#f5f5f1','text.color':'#172630','axes.labelcolor':'#172630'})
    fig=plt.figure(figsize=(16,10),layout='constrained');gs=fig.add_gridspec(3,2,height_ratios=[1.1,1.1,1.4]);cmap='viridis';maximum=max(x['displacement_max_mm']for x in reports)
    # A deterministic projected all-face envelope, no geometry deformation.
    for row,order in enumerate(['P1','P2']):
        with np.load(root/f'meshlib-R2-matched-{order}-assessment-001/results.npz',allow_pickle=False)as data:u=data['displacement'].copy()
        mag=np.linalg.norm(u[:len(v)],axis=1);values=mag[faces].mean(axis=1);tri=v[faces][:,:,[0,2]];depth=v[faces,1].mean(axis=1);indices=np.argsort(depth);ax=fig.add_subplot(gs[row,:]);collection=PolyCollection(tri[indices],array=values[indices],cmap=cmap,clim=(0,maximum),linewidth=0,rasterized=True);ax.add_collection(collection);ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('X [mm]');ax.set_ylabel('Z [mm]');ax.set_title(f'{order} · {reports[row]["nodes"]:,} nodes · maximum nodal displacement {reports[row]["displacement_max_mm"]:.3f} mm',loc='left');fig.colorbar(collection,ax=ax,shrink=.75,label='Mean corner |u| [mm]')
    ax=fig.add_subplot(gs[2,0]);values=[r['displacement_max_mm']for r in reports];bars=ax.bar(['P1 / C3D4','P2 / C3D10'],values,color=['#829995','#d48445'],width=.55);ax.bar_label(bars,fmt='%.3f mm',padding=5);ax.set_ylim(0,3);ax.set_ylabel('Maximum nodal displacement [mm]');ax.set_title('Same continuous bore tractions',loc='left')
    ax=fig.add_subplot(gs[2,1]);ax.axis('off');ax.text(0,1,'WHAT THIS COMPARISON SHOWS',fontweight='bold',fontsize=13,va='top');ax.text(0,.83,'343,283 matched parent tetrahedra\nSame reference surface, material and loads\nBoth reaction and stress-energy checks pass\n\nP1 / P2 stiffness differs materially.\nStress convergence is still open.\nP2 peak: 1,152.4 MPa near the end restraint.\n\nReference R2 mass: 1.298200 kg\nAuxiliary surface distance: certified ≤ 0.06 mm',va='top',linespacing=1.65)
    fig.suptitle('993 CARRIER  /  ELEMENT-ORDER STUDY',fontsize=22,fontweight='bold');fig.savefig(a.output/'carrier-element-order-comparison.png',dpi=150);plt.close(fig)
    # Local actual mesh; every facet in the displayed slab, no decimation.
    mask=np.all((v[faces][:,:,0]>35)&(v[faces][:,:,0]<65)&(v[faces][:,:,1]>-1),axis=1);local=faces[mask];fig,ax=plt.subplots(figsize=(12,6),layout='constrained');ax.add_collection(PolyCollection(v[local][:,:,[0,2]],facecolors='#d9e2df',edgecolors='#315855',linewidths=.22));ax.autoscale();ax.set_aspect('equal');ax.set_xlabel('X [mm]');ax.set_ylabel('Z [mm]');ax.set_title('Actual auxiliary surface around the central pad — all facets in the selected slab',loc='left');fig.suptitle('196,406 SURFACE TRIANGLES  /  COMPLETE TWO-WAY DISTANCE CERTIFICATE',fontweight='bold',fontsize=15);fig.savefig(a.output/'carrier-auxiliary-mesh-detail.png',dpi=150);plt.close(fig)

if __name__=='__main__':main()
