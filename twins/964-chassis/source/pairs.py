import numpy as np
d=np.load('loops.npz'); cent,diam,npts,circ=d['cent'],d['diam'],d['npts'],d['circ']
ok=(npts>=8)&(diam>10)&(diam<80)&(circ<0.25)
C=cent[ok]; D=diam[ok]
L=np.where(C[:,1]>0)[0]; R=np.where(C[:,1]<0)[0]
print(f"candidates: {len(L)} left, {len(R)} right")
targets={'P17 jack front':1330,'P18 jack rear':1236,'P19 platform rear':1018,
         'P5 outer x-mbr FA':770,'P21 engine mount':640,'P3 FA side member':610,
         'P20 front final':440,'P12 trans x-mbr':278,'P6 inner x-mbr FA':204}
XT=25.0   # same longitudinal station
found=[]
for i in L:
    for j in R:
        dx=C[i,0]-C[j,0]
        if abs(dx)>XT: continue
        span=C[i,1]-C[j,1]
        for nm,t in targets.items():
            if abs(span-t)<=4.0:
                found.append((nm,t,span,span-t,(C[i,0]+C[j,0])/2,dx,D[i],D[j],C[i,2],C[j,2]))
print(f"\nL/R pairs within 25mm in X and within 4mm of a published spacing: {len(found)}")
print(f"{'target':<20}{'nom':>6}{'measured':>10}{'err':>7}{'X mid':>10}{'dX':>7}{'diaL':>7}{'diaR':>7}{'Zl':>7}{'Zr':>7}")
for f in sorted(found,key=lambda r:abs(r[3])):
    print(f"{f[0]:<20}{f[1]:>6}{f[2]:>10.1f}{f[3]:>+7.1f}{f[4]:>10.1f}{f[5]:>+7.1f}{f[6]:>7.1f}{f[7]:>7.1f}{f[8]:>7.1f}{f[9]:>7.1f}")

# significance: how many pairs pass the X gate at all, and what spacing range do they cover?
allspans=[]
for i in L:
    for j in R:
        if abs(C[i,0]-C[j,0])<=XT: allspans.append(C[i,1]-C[j,1])
allspans=np.array(allspans)
print(f"\ntotal L/R pairs passing the X gate: {len(allspans)}")
print(f"their spacing range: {allspans.min():.0f} .. {allspans.max():.0f} mm")
width=8.0*len(targets)          # total accepting width (+-4mm around 9 targets)
rng=allspans.max()-allspans.min()
exp=len(allspans)*width/rng
print(f"expected chance matches if spacings were uniform: {exp:.1f}   observed: {len(found)}")
