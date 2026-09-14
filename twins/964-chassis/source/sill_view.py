import numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
V=np.load('verts_vehicle.npy')
fig,axes=plt.subplots(2,1,figsize=(20,11))
for ax,(lo,hi,lab) in zip(axes,[(520,820,'LEFT sill  Y +520..+820'),(-820,-520,'RIGHT sill Y -820..-520')]):
    s=(V[:,1]>lo)&(V[:,1]<hi)&(V[:,2]>60)&(V[:,2]<430)&(V[:,0]>-2100)&(V[:,0]<300)
    P=V[s]
    H,xe,ye=np.histogram2d(P[:,0],P[:,1],bins=[600,150],weights=P[:,2])
    C,_,_ =np.histogram2d(P[:,0],P[:,1],bins=[600,150])
    M=np.where(C>0,H/np.maximum(C,1),np.nan)
    im=ax.imshow(M.T,origin='lower',extent=[xe[0],xe[-1],ye[0],ye[-1]],cmap='turbo',aspect='equal')
    plt.colorbar(im,ax=ax,label='Z mm',shrink=.8)
    ax.set_title(f'{lab}   ({len(P):,} pts)  — white = no data (holes/occlusion)')
    ax.set_xlabel('X forward mm'); ax.set_ylabel('Y mm')
    for y in (665,-665,618,-618,509,-509):
        if lo<y<hi: ax.axhline(y,color='w',lw=1,ls='--')
    ax.grid(alpha=.3,lw=.3)
plt.tight_layout(); plt.savefig('sill.png',dpi=68)
print('saved sill.png')
