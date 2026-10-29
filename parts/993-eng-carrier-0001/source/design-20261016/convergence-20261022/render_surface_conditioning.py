"""Render actual local triangles and whole-mesh conditioning measurements."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm


def load(path):
    z=np.load(path,allow_pickle=False);v=z['vertices'];f=z['triangles'];t=v[f];n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);area=np.linalg.norm(n,axis=1);longest=np.linalg.norm(np.stack([t[:,1]-t[:,0],t[:,2]-t[:,1],t[:,0]-t[:,2]],1),axis=2).max(1);return v,f,longest**2/area


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--original',type=Path,required=True);p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('Fresh image required')
    original=load(a.original);before=load(a.before);after=load(a.after);v,f,ar=before;i=int(ar.argmax());t=v[f[i]];centre=t.mean(0);edges=np.asarray([t[1]-t[0],t[2]-t[1],t[0]-t[2]]);u=edges[np.linalg.norm(edges,axis=1).argmax()];u/=np.linalg.norm(u);normal=np.cross(t[1]-t[0],t[2]-t[0]);normal/=np.linalg.norm(normal);b=np.cross(normal,u);fig=plt.figure(figsize=(16,6.8),facecolor='#f6f7f9');grid=fig.add_gridspec(1,3,width_ratios=[1,1,.9],left=.055,right=.975,top=.81,bottom=.29,wspace=.32);cmap=plt.get_cmap('magma');scale=LogNorm(1,1e6)
    for col,(label,data)in enumerate([('Before local corrections',before),('After verified local corrections',after)]):
        ax=fig.add_subplot(grid[0,col]);vertices,faces,quality=data;triangles=vertices[faces];centres=triangles.mean(1);ids=np.flatnonzero(np.linalg.norm(centres-centre,axis=1)<.34);local=triangles[ids];normals=np.cross(local[:,1]-local[:,0],local[:,2]-local[:,0]);valid=(normals@normal)>.35*np.linalg.norm(normals,axis=1);ids=ids[valid];local=triangles[ids]-centre;projected=np.stack([local@u,local@b],axis=2);collection=PolyCollection(projected,array=quality[ids],cmap=cmap,norm=scale,edgecolors='#555a66',linewidths=.45);ax.add_collection(collection);ax.set(xlim=(-.28,.28),ylim=(-.28,.28),xlabel='Local tangent u (mm)',ylabel='Local tangent v (mm)',title=label);ax.set_aspect('equal');ax.set_facecolor('white');ax.grid(alpha=.12);ax.tick_params(labelsize=8)
    ax=fig.add_subplot(grid[0,2]);datasets=[original,before,after];names=['Ported\ninput','CGAL\nremesh','Final\nsurface'];maximum=[float(d[2].max())for d in datasets];bad=[int((d[2]>100).sum())for d in datasets];bars=ax.bar(names,maximum,color=['#b44b41','#dc9852','#2a766c'],width=.6);ax.set_yscale('log');ax.set_ylim(1,3e9);ax.axhline(100,color='#5e6672',linestyle='--',linewidth=.9);ax.set_ylabel('Worst triangle aspect ratio (log scale)');ax.set_title('Entire carrier: every triangle');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    for bar,value,count in zip(bars,maximum,bad):ax.text(bar.get_x()+bar.get_width()/2,value*1.45,f'{value:,.1f}\n{count} above 100',ha='center',va='bottom',fontsize=9)
    fig.suptitle('993 engine carrier | Surface conditioning',x=.055,ha='left',fontsize=21,fontweight='bold',color='#172534');fig.text(.055,.868,'Actual mesh data · identical local views · protected interface triangles preserved',fontsize=11,color='#465565');fig.text(.055,.035,f'Local view centred at ({centre[0]:.3f}, {centre[1]:.3f}, {centre[2]:.3f}) mm.  AR = longest edge / altitude.\nColour shows AR on the same logarithmic scale; the right panel measures the complete meshes.',fontsize=9,color='#465565');colour_ax=fig.add_axes([.11,.16,.43,.018]);colourbar=fig.colorbar(plt.cm.ScalarMappable(norm=scale,cmap=cmap),cax=colour_ax,orientation='horizontal');colourbar.set_label('Triangle aspect ratio',fontsize=8);colourbar.ax.tick_params(labelsize=8);a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=180,facecolor=fig.get_facecolor());plt.close(fig);print(str(a.output))

if __name__=='__main__':main()
