import numpy as np
V=np.load('verts_vehicle.npy')
# floor pan: the big flat band. find its height
core=(V[:,0]>-1400)&(V[:,0]<-200)&(np.abs(V[:,1])<450)
z=V[core][:,2]
h,edges=np.histogram(z,bins=200)
zf=(edges[h.argmax()]+edges[h.argmax()+1])/2
print(f"floor pan height above ground Z = {zf:.1f} mm   (mode of {core.sum():,} pts)")
print(f"  floor pan Z spread p5..p95: {np.percentile(z,5):.1f} .. {np.percentile(z,95):.1f}")
# sill outer edge vs X: widest structure below 400mm
print(f"\n{'X station':>10}{'left edge Y':>13}{'right edge Y':>14}{'width':>9}")
for x0 in range(-2000,401,200):
    s=(V[:,0]>x0-60)&(V[:,0]<x0+60)&(V[:,2]>60)&(V[:,2]<420)
    if s.sum()<500: continue
    Y=V[s][:,1]
    l,r=np.percentile(Y,99.5),np.percentile(Y,0.5)
    print(f"{x0:>10}{l:>13.1f}{r:>14.1f}{l-r:>9.1f}")
# central tunnel: height profile across Y at mid-floor
s=(V[:,0]>-1200)&(V[:,0]<-800)&(V[:,2]>60)&(V[:,2]<500)
Y=V[s][:,1]; Z=V[s][:,2]
print(f"\ntunnel section at X=-1000 (mean Z per 40mm Y bin):")
for yy in range(-360,361,60):
    m=(Y>yy-20)&(Y<yy+20)
    if m.sum()>50: print(f"   Y={yy:>5}  Zmax={Z[m].max():6.1f}  Zmean={Z[m].mean():6.1f}")
