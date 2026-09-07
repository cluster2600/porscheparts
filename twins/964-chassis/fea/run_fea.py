"""Torsion load case on the 964 floor shell model, CalculiX.

Usage: run_fea.py <thickness_mm> <tag> [E_MPa] [nu] [G_MPa]
E and nu default to steel, so the historic two-argument calls are unchanged.
"""
import numpy as np, subprocess, os, sys, re, pathlib
T=float(sys.argv[1]); tag=sys.argv[2]
E  = float(sys.argv[3]) if len(sys.argv)>3 else 210000.0   # MPa
NU = float(sys.argv[4]) if len(sys.argv)>4 else 0.3
# G optionnel. Absent, le materiau est isotrope et G decoule de E et nu : tous
# les appels historiques sont donc inchanges. Present, il est impose
# INDEPENDAMMENT de E, ce qui rend le materiau non physique et c'est voulu :
# c'est le seul moyen de faire apprendre a un substitut la difference entre
# flexion et cisaillement, que dominance_study.py a montree decisive ici.
G  = float(sys.argv[5]) if len(sys.argv)>5 else None
# Meme repertoire de travail que build_body.py : voir le commentaire qui y est.
WORK=os.environ.get('FEA_WORK','.')
d=np.load(os.path.join(WORK,'mesh.npz')); nid,xyz,tri=d['nid'],d['xyz'],d['tri']
# Ordre d'element lu dans le maillage, jamais suppose. Les triangles lineaires S3
# sont trop raides en flexion : sur le plancher nu, ils rendent 2442 N.m/deg la
# ou les S6 rendent 1446, et ils attribuent a G une sensibilite que le meme
# modele en S6 n'a pas. Sur les architectures fermees les deux s'accordent.
ORDER=int(d['order']) if 'order' in d.files else 1
cells = d['cells'] if 'cells' in d.files else tri
ETYPE = 'S6' if ORDER == 2 else 'S3'
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
def write_inp(solver_kw):
  with open(pathlib.Path(WORK, f'{tag}.inp'),'w') as f:
      f.write("*NODE, NSET=NALL\n")
      for n,p in zip(nid,xyz): f.write(f"{int(n)}, {p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}\n")
      f.write(f"*ELEMENT, TYPE={ETYPE}, ELSET=SHELL\n")
      for i,e in enumerate(cells,1):
          f.write(f"{i}, " + ", ".join(str(int(v)) for v in e) + "\n")
      f.write(f"*SHELL SECTION, ELSET=SHELL, MATERIAL=MAT\n{T}\n")
      if G is None:
          f.write(f"*MATERIAL, NAME=MAT\n*ELASTIC\n{E}, {NU}\n")
      else:
          f.write("*MATERIAL, NAME=MAT\n*ELASTIC, TYPE=ENGINEERING CONSTANTS\n")
          f.write(f"{E}, {E}, {E}, {NU}, {NU}, {NU}, {G}, {G}\n{G}\n")
      for nm,st in (('REAR',rear),('FRL',frL),('FRR',frR)):
          f.write(f"*NSET, NSET={nm}\n")
          for i in range(0,len(st),8): f.write(", ".join(str(int(x)) for x in st[i:i+8])+",\n")
      f.write("*BOUNDARY\nREAR, 1, 6\n")
      f.write(f"*STEP\n*STATIC{solver_kw}\n")
      f.write(f"*CLOAD\nFRL, 3, {F/max(len(frL),1):.6f}\nFRR, 3, {-F/max(len(frR),1):.6f}\n")
      f.write("*NODE FILE, OUTPUT=2D\nU\n*EL FILE, OUTPUT=2D\nS\n*END STEP\n")
# Le .frd d'une execution precedente doit disparaitre AVANT l'appel au solveur.
# Sinon un echec de ccx laisse un fichier lisible en place et le depouillement
# rend, sans rien signaler, le resultat du run precedent.
env=dict(os.environ)
S='/home/maxime/work/964twin/syslibs/usr/lib/x86_64-linux-gnu'
env['LD_LIBRARY_PATH']=f"{S}:{S}/lapack:{S}/blas:{S}/openmpi/lib"
env['OMP_NUM_THREADS']=os.environ.get('OMP_NUM_THREADS','4')

# Repli de solveur. Sur certaines geometries, SPOOLES meurt pendant la
# factorisation avec « fatal error in GPart_makeYCmap / bad input » : un defaut
# de son partitionnement de graphe, pas un modele mal pose. C'est deterministe,
# insensible au nombre de fils, et cela a coute 11 cas du corpus — tous de la
# meme architecture, donc un trou oriente et non du bruit. Le solveur iteratif
# de CalculiX passe sur ces memes cas. Il n'est PAS utilise par defaut : le
# resultat retenu reste celui de SPOOLES partout ou il aboutit.
# Le repli iteratif doit etre borne dans le temps. Sur un maillage S6 il a tourne
# douze minutes sans aboutir et a bloque une campagne entiere : un solveur
# iteratif qui ne converge pas ne rend pas d'erreur, il rend du temps.
LIMITE = float(os.environ.get('CCX_TIMEOUT', '600'))
SOLVERS = [("", "spooles"), (", SOLVER=ITERATIVE CHOLESKY", "iterative_cholesky")]
if os.environ.get('CCX_SOLVER') == 'iterative':
    SOLVERS = SOLVERS[1:]
for kw, solver in SOLVERS:
    write_inp(kw)
    for ext in ('.frd', '.dat', '.sta', '.cvg', '.12d'):
        pathlib.Path(WORK, tag + ext).unlink(missing_ok=True)
    try:
        r=subprocess.run(['/home/maxime/work/964twin/syslibs/usr/bin/ccx','-i',tag],
                         capture_output=True,text=True,env=env,cwd=WORK,timeout=LIMITE)
    except subprocess.TimeoutExpired:
        print(f"[{solver}] depassement de {LIMITE:.0f}s, abandon"); continue
    if 'Job finished' in r.stdout: break
    # SPOOLES ecrit son erreur fatale sur stderr, que ce script ignorait : un
    # echec n'affichait donc que la derniere ligne normale de stdout.
    print(f"[{solver}] {r.stdout[-800:]}\n[{solver}/stderr] {r.stderr[-400:]}")
else:
    sys.exit(1)

# read displacements from .frd
uz={}; vm={}
mode=None
coord={}
for line in open(pathlib.Path(WORK, f'{tag}.frd')):
    if '    2C' in line[:8]: mode='C'; continue
    if ' -4  DISP' in line: mode='U'; continue
    if ' -4  STRESS' in line: mode='S'; continue
    if line.startswith(' -3'): mode=None; continue
    if mode=='C' and line.startswith(' -1'):
        coord[int(line[3:13])]=(float(line[13:25]),float(line[25:37]),float(line[37:49]))
    if mode=='U' and line.startswith(' -1'):
        uz[int(line[3:13])]=float(line[37:49])
    if mode=='S' and line.startswith(' -1'):
        v=[float(line[13+12*k:25+12*k]) for k in range(6)]
        sx,sy,sz,sxy,syz,sxz=v
        vm[int(line[3:13])]=np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2)+3*(sxy**2+syz**2+sxz**2))
# Fail-closed. La moyenne ne doit porter que sur des noeuds effectivement lus
# dans le .frd : filtrer silencieusement les manquants a produit des raideurs
# fausses de plusieurs pour cent, sans aucun signe exterieur.
if ORDER == 2:
    # En S6, CalculiX etend le modele en 3D et ignore OUTPUT=2D : la numerotation
    # du .frd n'est plus celle du maillage. Les noeuds de mesure sont donc repris
    # PAR LEUR GEOMETRIE, ce qui ne depend d'aucune correspondance de numeros.
    if len(uz) < len(nid):
        sys.exit(f"{tag}: {len(uz)} deplacements lus pour {len(nid)} noeuds du maillage")
    gl = lambda sgn: [n for n,q in coord.items()
                      if q[0] > X_F-8 and q[2] < Z0+SILL_H+1 and sgn*q[1] > YS_I-1]
    frL, frR = gl(1), gl(-1)
    if not frL or not frR:
        sys.exit(f"{tag}: aucun noeud charge retrouve par la geometrie")
else:
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
      f"uz L{zl:+7.3f} R{zr:+7.3f} mm | vM p99 {np.percentile(s,99):6.1f} MPa max {s.max():6.1f}"
      f"{'' if solver=='spooles' else ' | solveur ' + solver}")
np.savez(pathlib.Path(WORK, f'{tag}_res.npz'),K=K,theta=theta,E=E,nu=NU,solver=solver,vm=np.array(list(vm.values())),
         vmn=np.array(list(vm.keys())),torque=torque,T=T)
