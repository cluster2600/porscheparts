import numpy as np
d=np.load('loops.npz'); cent,diam,npts,circ=d['cent'],d['diam'],d['npts'],d['circ']
ok=(npts>=8)&(diam>10)&(diam<80)&(circ<0.25)
C=cent[ok]; D=diam[ok]
L=np.where(C[:,1]>0)[0]; R=np.where(C[:,1]<0)[0]
targets={'P17':1330,'P18':1236,'P19':1018,'P5':770,'P21':640,'P3':610,'P20':440,'P12':278,'P6':204}
print("A genuine datum pair must match in X, in Z, and in hole diameter.")
print(f"{'gate':<52}{'matches':>9}")
for lab,(xt,zt,dt,st) in {
    'X within 25mm, spacing within 4mm (previous)':(25,9e9,9e9,4),
    '+ same height  |dZ| < 20mm':(25,20,9e9,4),
    '+ similar diameter |dDia| < 8mm':(25,20,8,4),
    '+ spacing within 1mm (published tolerance)':(25,20,8,1),
}.items():
    n=0; hits=[]
    for i in L:
        for j in R:
            if abs(C[i,0]-C[j,0])>xt: continue
            if abs(C[i,2]-C[j,2])>zt: continue
            if abs(D[i]-D[j])>dt: continue
            sp=C[i,1]-C[j,1]
            for nm,t in targets.items():
                if abs(sp-t)<=st: n+=1; hits.append((nm,sp,(C[i,0]+C[j,0])/2))
    print(f"{lab:<52}{n:>9}")
    last=hits
print()
if last:
    for nm,sp,x in last: print(f"   {nm}: spacing {sp:.1f} at X={x:.1f}")
else:
    print("   no pair survives all four gates.")
# specifically P17
print("\nAny L/R pair with spacing 1330 +/- 10 mm, at any X offset?")
n17=0
for i in L:
    for j in R:
        sp=C[i,1]-C[j,1]
        if abs(sp-1330)<=10:
            n17+=1
            print(f"   spacing {sp:.1f}  Xl={C[i,0]:.0f} Xr={C[j,0]:.0f}  dX={C[i,0]-C[j,0]:+.0f}  dZ={C[i,2]-C[j,2]:+.0f}")
if not n17: print("   none.")
