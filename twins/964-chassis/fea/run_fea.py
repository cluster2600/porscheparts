"""Torsion load case on the 964 floor shell model, CalculiX.

Usage: run_fea.py <thickness_mm> <tag> [E_MPa] [nu]
E and nu default to steel, so the historic two-argument calls are unchanged.
"""
import numpy as np, subprocess, os, sys, re, pathlib
T=float(sys.argv[1]); tag=sys.argv[2]
E  = float(sys.argv[3]) if len(sys.argv)>3 else 210000.0   # MPa
NU = float(sys.argv[4]) if len(sys.argv)>4 else 0.3
d=np.load('mesh.npz'); nid,xyz,tri=d['nid'],d['xyz'],d['tri']
idx={int(n):i for i,n in enumerate(nid)}
YS_I,SILL_W,SILL_H,Z0=600.0,90.0,120.0,271.7
X_F,X_R=float(xyz[:,0].max()),float(xyz[:,0].min())   # bornes lues au maillage,
# et non recopiees du script de construction : elles ne peuvent plus diverger.
ARM=2*(YS_I+SILL_W/2)                      # moment arm between sill load lines (mm)
F=1000.0                                   # N per side
# node sets
rear = nid[xyz[:,0] < X_R+8]                                       # clamp
# Le couple s'applique, et la rotation se mesure, sur la SECTION DE LONGERON
# seule : bande z entre le fond et le dessus du longeron. Sans cette borne en z,
# le jeu de noeuds charges grossit avec l'architecture — bord de tablier, equerre
# de passage de roue, pied de montant A viennent s'y ajouter — et deux
# architectures ne se comparent plus sous le meme chargement.
band = (xyz[:,0] > X_F-8) & (xyz[:,2] < Z0+SILL_H+1)
frL  = nid[band & (xyz[:,1] >  YS_I-1)]                            # front left sill
frR  = nid[band & (xyz[:,1] < -YS_I+1)]                            # front right sill
with open(f'{tag}.inp','w') as f:
    f.write("*NODE, NSET=NALL\n")
    for n,p in zip(nid,xyz): f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
    f.write("*ELEMENT, TYPE=S3, ELSET=SHELL\n")
    for i,e in enumerate(tri,1): f.write(f"{i}, {int(e[0])}, {int(e[1])}, {int(e[2])}\n")
    f.write(f"*SHELL SECTION, ELSET=SHELL, MATERIAL=MAT\n{T}\n")
    f.write(f"*MATERIAL, NAME=MAT\n*ELASTIC\n{E}, {NU}\n")
    for nm,st in (('REAR',rear),('FRL',frL),('FRR',frR)):
        f.write(f"*NSET, NSET={nm}\n")
        for i in range(0,len(st),8): f.write(", ".join(str(int(x)) for x in st[i:i+8])+",\n")
    f.write("*BOUNDARY\nREAR, 1, 6\n")
    f.write("*STEP\n*STATIC\n")
    f.write(f"*CLOAD\nFRL, 3, {F/max(len(frL),1):.6f}\nFRR, 3, {-F/max(len(frR),1):.6f}\n")
    f.write("*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n*END STEP\n")
# Le .frd d'une execution precedente doit disparaitre AVANT l'appel au solveur.
# Sinon un echec de ccx laisse un fichier lisible en place et le depouillement
# rend, sans rien signaler, le resultat du run precedent.
for ext in ('.frd', '.dat', '.sta', '.cvg', '.12d'):
    pathlib.Path(tag + ext).unlink(missing_ok=True)
env=dict(os.environ)
S='/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
env['LD_LIBRARY_PATH']=f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
env['OMP_NUM_THREADS']=os.environ.get('OMP_NUM_THREADS','4')
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
# Fail-closed. La moyenne ne doit porter que sur des noeuds effectivement lus
# dans le .frd : filtrer silencieusement les manquants a produit des raideurs
# fausses de plusieurs pour cent, sans aucun signe exterieur.
if len(uz) != len(nid):
    sys.exit(f"{tag}: {len(uz)} deplacements lus pour {len(nid)} noeuds du maillage")
missing = [int(n) for n in np.concatenate([frL, frR]) if int(n) not in uz]
if missing:
    sys.exit(f"{tag}: {len(missing)} noeuds charges absents du .frd")
zl=np.mean([uz[int(n)] for n in frL])
zr=np.mean([uz[int(n)] for n in frR])
theta=np.degrees(np.arctan((zl-zr)/ARM))
torque=F*ARM/1000.0                                    # N.m
K=torque/theta if theta else float('nan')
s=np.array(list(vm.values()))
print(f"E={E:>7.0f} nu={NU:.3f} | t={T:>5} mm | twist {theta:7.4f} deg | K = {K:8.0f} N.m/deg | "
      f"uz L{zl:+7.3f} R{zr:+7.3f} mm | vM p99 {np.percentile(s,99):6.1f} MPa max {s.max():6.1f}")
np.savez(f'{tag}_res.npz',K=K,theta=theta,E=E,nu=NU,vm=np.array(list(vm.values())),
         vmn=np.array(list(vm.keys())),torque=torque,T=T)
