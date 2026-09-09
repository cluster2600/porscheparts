import numpy as np, trimesh
from trimesh.graph import connected_components
yaw,x0,roll = np.load('sym_plane.npy')
m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
V=np.asarray(m.vertices).copy(); F=m.faces

# 1. move centreline to X=0, then undo yaw and roll so the symmetry plane is X=0
V[:,0]-=x0
cz,sz=np.cos(-yaw),np.sin(-yaw)                      # about Z
V[:,[0,1]] = np.c_[V[:,0]*cz - V[:,1]*sz, V[:,0]*sz + V[:,1]*cz]
cy,sy=np.cos(-roll),np.sin(-roll)                    # about Y
V[:,[0,2]] = np.c_[V[:,0]*cy + V[:,2]*sy, -V[:,0]*sy + V[:,2]*cy]

# 2. re-fit wheels in the corrected frame
cc = sorted(connected_components(m.face_adjacency, nodes=np.arange(len(F)), engine='scipy'), key=len, reverse=True)
def fit_circle(y,z):
    A=np.c_[y,z,np.ones(len(y))]; b=y**2+z**2
    for _ in range(15):
        sol,*_=np.linalg.lstsq(A,b,rcond=None); cy_,cz_=sol[0]/2,sol[1]/2
        r=np.sqrt(sol[2]+cy_**2+cz_**2); d=np.abs(np.hypot(y-cy_,z-cz_)-r)
        w=1.0/(1.0+(d/max(np.median(d)*3,1.0))**2)
        A=np.c_[y,z,np.ones(len(y))]*w[:,None]; b=(y**2+z**2)*w
    return cy_,cz_,r
names={1:'rear RIGHT',2:'front RIGHT',3:'front LEFT',4:'rear LEFT'}
W={}
for i in (1,2,3,4):
    vi=np.unique(F[cc[i]].ravel()); P=V[vi]
    cyy,czz,r=fit_circle(P[:,1],P[:,2]); W[i]=(cyy,czz,r,P[:,0].mean())
    print(f"{names[i]:<12} axleY={cyy:8.1f}  axleZ={czz:7.1f}  R={r:6.1f}  Xmean={P[:,0].mean():7.1f}")
fY=(W[2][0]+W[3][0])/2; rY=(W[1][0]+W[4][0])/2
print(f"\nwheelbase (corrected) = {fY-rY:.1f} mm   vs factory 2272  -> {fY-rY-2272:+.1f} mm")
print(f"L/R front axle Y mismatch: {abs(W[2][0]-W[3][0]):.1f} mm   (was 66.7 before correction)")
print(f"L/R rear  axle Y mismatch: {abs(W[1][0]-W[4][0]):.1f} mm   (was 51.1 before correction)")
ground = np.mean([W[i][1]-W[i][2] for i in (1,2,3,4)])
print(f"ground plane Z (mean tyre contact) = {ground:.1f}  spread {np.ptp([W[i][1]-W[i][2] for i in (1,2,3,4)]):.1f} mm")

# 3. ADR-0003 vehicle frame: origin on symmetry plane, above front axle, on ground.
#    X forward, Y left, Z up.   scan(+Y)=forward, scan(+X)=right  ->  Xv=Ys-fY, Yv=-Xs, Zv=Zs-ground
Vv = np.c_[ V[:,1]-fY, -V[:,0], V[:,2]-ground ]
np.save('verts_vehicle.npy', Vv.astype(np.float32))
np.save('faces.npy', F.astype(np.int32))
print(f"\nVEHICLE FRAME extents  X(fwd) {Vv[:,0].min():8.1f}..{Vv[:,0].max():8.1f}")
print(f"                       Y(left){Vv[:,1].min():8.1f}..{Vv[:,1].max():8.1f}")
print(f"                       Z(up)  {Vv[:,2].min():8.1f}..{Vv[:,2].max():8.1f}")
np.save('frame_params.npy', np.array([yaw,x0,roll,fY,ground]))
