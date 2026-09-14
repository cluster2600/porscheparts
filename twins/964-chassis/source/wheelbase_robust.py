import numpy as np, trimesh
from trimesh.graph import connected_components
from scipy.optimize import least_squares
yaw,x0,roll=np.load('sym_plane.npy')
m=trimesh.load('raw/964widebodyunderside2poin13.obj',process=False)
V=np.asarray(m.vertices).copy(); F=m.faces
V[:,0]-=x0
cz,sz=np.cos(-yaw),np.sin(-yaw); V[:,[0,1]]=np.c_[V[:,0]*cz-V[:,1]*sz, V[:,0]*sz+V[:,1]*cz]
cy_,sy_=np.cos(-roll),np.sin(-roll); V[:,[0,2]]=np.c_[V[:,0]*cy_+V[:,2]*sy_, -V[:,0]*sy_+V[:,2]*cy_]
cc=sorted(connected_components(m.face_adjacency,nodes=np.arange(len(F)),engine='scipy'),key=len,reverse=True)
W={i:V[np.unique(F[cc[i]].ravel())] for i in (1,2,3,4)}
names={1:'rear R',2:'front R',3:'front L',4:'rear L'}
def arc_span(P,cy,cz2):
    a=np.arctan2(P[:,2]-cz2,P[:,1]-cy); return np.degrees(np.ptp(a))
def fit_free(P):
    def res(p): return np.hypot(P[:,1]-p[0],P[:,2]-p[1])-p[2]
    r=least_squares(res,[P[:,1].mean(),P[:,2].mean(),280],loss='cauchy',f_scale=8)
    return r.x
def fit_fixedR(P,R):
    def res(p): return np.hypot(P[:,1]-p[0],P[:,2]-p[1])-R
    r=least_squares(res,[P[:,1].mean(),P[:,2].mean()],loss='cauchy',f_scale=8)
    return r.x
print("free fit — and how much of the circle the scan actually covers:")
free={}
for i in (1,2,3,4):
    cy,czz,R=fit_free(W[i]); free[i]=(cy,czz,R)
    print(f"  {names[i]:<8} cY={cy:8.1f}  R={R:6.1f}  OD={2*R:6.1f}  arc covered {arc_span(W[i],cy,czz):5.0f} deg")
fY=(free[2][0]+free[3][0])/2; rY=(free[1][0]+free[4][0])/2
print(f"  -> wheelbase {fY-rY:.1f}")
print("\nsensitivity: refit with radius FIXED at plausible tyre sizes")
print(f"{'OD assumed':>11}{'front axle':>12}{'rear axle':>11}{'wheelbase':>11}{'vs 2272':>9}")
for OD in (560,600,620,632,650,680):
    c={i:fit_fixedR(W[i],OD/2) for i in (1,2,3,4)}
    f=(c[2][0]+c[3][0])/2; r=(c[1][0]+c[4][0])/2
    print(f"{OD:>11}{f:>12.1f}{r:>11.1f}{f-r:>11.1f}{f-r-2272:>+9.1f}")
