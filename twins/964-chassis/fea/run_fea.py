"""Torsion load case on the 964 floor shell model, CalculiX."""
import numpy as np, subprocess, os, sys, re
T=float(sys.argv[1]); tag=sys.argv[2]
d=np.load('mesh.npz'); nid,xyz,tri=d['nid'],d['xyz'],d['tri']
idx={int(n):i for i,n in enumerate(nid)}
X_F,X_R,YS_I,SILL_W,Z0=400.0,-1500.0,600.0,90.0,271.7
ARM=2*(YS_I+SILL_W/2)                      # moment arm between sill load lines (mm)
F=1000.0                                   # N per side
# node sets
rear = nid[xyz[:,0] < X_R+8]                                       # clamp
frL  = nid[(xyz[:,0] > X_F-8) & (xyz[:,1] >  YS_I-1)]              # front left sill
frR  = nid[(xyz[:,0] > X_F-8) & (xyz[:,1] < -YS_I+1)]              # front right sill
with open(f'{tag}.inp','w') as f:
    f.write("*NODE, NSET=NALL\n")
    for n,p in zip(nid,xyz): f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
    f.write("*ELEMENT, TYPE=S3, ELSET=SHELL\n")
    for i,e in enumerate(tri,1): f.write(f"{i}, {int(e[0])}, {int(e[1])}, {int(e[2])}\n")
    f.write(f"*SHELL SECTION, ELSET=SHELL, MATERIAL=STEEL\n{T}\n")
    f.write("*MATERIAL, NAME=STEEL\n*ELASTIC\n210000., 0.3\n")
    for nm,st in (('REAR',rear),('FRL',frL),('FRR',frR)):
        f.write(f"*NSET, NSET={nm}\n")
        for i in range(0,len(st),8): f.write(", ".join(str(int(x)) for x in st[i:i+8])+",\n")
    f.write("*BOUNDARY\nREAR, 1, 6\n")
    f.write("*STEP\n*STATIC\n")
    f.write(f"*CLOAD\nFRL, 3, {F/max(len(frL),1):.6f}\nFRR, 3, {-F/max(len(frR),1):.6f}\n")
    f.write("*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n*END STEP\n")
env=dict(os.environ)
S='/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
env['LD_LIBRARY_PATH']=f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
env['OMP_NUM_THREADS']='4'
r=subprocess.run(['/home/maxime/work/964twin/syslibs/usr/bin/ccx','-i',tag],
                 capture_output=True,text=True,env=env,cwd='.')
if 'Job finished' not in r.stdout: print(r.stdout[-1200:]); sys.exit(1)
# read displacements from .frd
uz={}; vm={}
mode=None
for line in open(f'{tag}.frd'):
    if ' -4  DISP' in line: mode='U'; continue
    if ' -4  STRESS' in line: mode='S'; continue
    if line.startswith(' -3'): mode=None; continue
    if mode=='U' and line.startswith(' -1'):
        uz[int(line[3:13])]=float(line[37:49])
    if mode=='S' and line.startswith(' -1'):
        v=[float(line[13+12*k:25+12*k]) for k in range(6)]
        sx,sy,sz,sxy,syz,sxz=v
        vm[int(line[3:13])]=np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(sxy**2+syz**2+sxz**2))
zl=np.mean([uz[int(n)] for n in frL if int(n) in uz])
zr=np.mean([uz[int(n)] for n in frR if int(n) in uz])
theta=np.degrees(np.arctan((zl-zr)/ARM))
torque=F*ARM/1000.0                                    # N.m
K=torque/theta if theta else float('nan')
s=np.array(list(vm.values()))
print(f"t={T:>4} mm | twist {theta:7.4f} deg | K = {K:8.0f} N.m/deg | "
      f"uz L{zl:+7.3f} R{zr:+7.3f} mm | vM p99 {np.percentile(s,99):6.1f} MPa max {s.max():6.1f}")
np.savez(f'{tag}_res.npz',K=K,theta=theta,vm=np.array(list(vm.values())),
         vmn=np.array(list(vm.keys())),torque=torque,T=T)
