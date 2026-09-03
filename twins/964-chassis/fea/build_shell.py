"""Shell FE model of the 964 floor assembly. Sheet metal -> shell elements, not solids."""
import gmsh, numpy as np, sys
T   = float(sys.argv[1]) if len(sys.argv)>1 else 1.0    # sheet thickness mm
LC  = float(sys.argv[2]) if len(sys.argv)>2 else 1.0    # mesh size factor
X_F, X_R = 400.0, -1500.0          # floor extent (SCAN)
YS_I, SILL_W, SILL_H = 600.0, 90.0, 120.0
Z0 = 271.7
XM = {'front_floor':21.3, 'seat_base':-506.0, 'trans':-1703.0}   # datum-placed crossmembers
XW, XH = 80.0, 70.0

gmsh.initialize(); gmsh.option.setNumber("General.Terminal",0)
gmsh.model.add("floor")
occ=gmsh.model.occ
def rect(p1,p2,p3,p4):
    ts=[occ.addPoint(*p) for p in (p1,p2,p3,p4)]
    ls=[occ.addLine(ts[i],ts[(i+1)%4]) for i in range(4)]
    return occ.addPlaneSurface([occ.addCurveLoop(ls)])
S={}
# floor plate
S['floor']=[rect((X_R,-YS_I,Z0),(X_F,-YS_I,Z0),(X_F,YS_I,Z0),(X_R,YS_I,Z0))]
# sills: closed box section each side
for nm,sgn in (('sill_L',1),('sill_R',-1)):
    yi,yo = sgn*YS_I, sgn*(YS_I+SILL_W)
    S[nm]=[rect((X_R,yi,Z0),(X_F,yi,Z0),(X_F,yo,Z0),(X_R,yo,Z0)),                       # bottom
           rect((X_R,yi,Z0+SILL_H),(X_F,yi,Z0+SILL_H),(X_F,yo,Z0+SILL_H),(X_R,yo,Z0+SILL_H)),
           rect((X_R,yi,Z0),(X_F,yi,Z0),(X_F,yi,Z0+SILL_H),(X_R,yi,Z0+SILL_H)),          # inner web
           rect((X_R,yo,Z0),(X_F,yo,Z0),(X_F,yo,Z0+SILL_H),(X_R,yo,Z0+SILL_H))]          # outer web
# crossmembers: open channel under the floor, spanning sill to sill
for nm,x in XM.items():
    a,b=x-XW/2,x+XW/2
    S[nm]=[rect((a,-YS_I,Z0-XH),(b,-YS_I,Z0-XH),(b,YS_I,Z0-XH),(a,YS_I,Z0-XH)),          # bottom
           rect((a,-YS_I,Z0-XH),(a,-YS_I,Z0),(a,YS_I,Z0),(a,YS_I,Z0-XH)),                # web
           rect((b,-YS_I,Z0-XH),(b,-YS_I,Z0),(b,YS_I,Z0),(b,YS_I,Z0-XH))]
occ.synchronize()
occ.removeAllDuplicates(); occ.synchronize()
gmsh.option.setNumber("Mesh.MeshSizeMin",25*LC); gmsh.option.setNumber("Mesh.MeshSizeMax",45*LC)
gmsh.model.mesh.generate(2)
nt,nc,_=gmsh.model.mesh.getNodes(); nc=nc.reshape(-1,3)
et,eT,eN=gmsh.model.mesh.getElements(2)
tri=np.concatenate([eN[i].reshape(-1,3) for i,t in enumerate(et) if t==2]) if 2 in et else np.zeros((0,3),int)
quad=np.concatenate([eN[i].reshape(-1,4) for i,t in enumerate(et) if t==3]) if 3 in et else np.zeros((0,4),int)
np.savez('mesh.npz',nid=nt,xyz=nc,tri=tri,quad=quad,T=T)
print(f"nodes {len(nt):,}  tri {len(tri):,}  quad {len(quad):,}  thickness {T} mm")
gmsh.finalize()
