import numpy as np, trimesh
from trimesh.graph import connected_components
m = trimesh.load('raw/964widebodyunderside2poin13.obj', process=False)
cc = sorted(connected_components(m.face_adjacency, nodes=np.arange(len(m.faces)), engine='scipy'), key=len, reverse=True)
V,F = m.vertices, m.faces

def fit_circle(y,z):
    """Algebraic (Kasa) circle fit + robust IRLS refinement -> tyre outer radius/centre."""
    A=np.c_[y,z,np.ones(len(y))]; b=y**2+z**2
    for _ in range(12):
        sol,*_ = np.linalg.lstsq(A,b,rcond=None)
        cy,cz = sol[0]/2, sol[1]/2
        r = np.sqrt(sol[2]+cy**2+cz**2)
        d = np.abs(np.hypot(y-cy,z-cz)-r)
        s = max(np.median(d)*3, 1.0)
        w = 1.0/(1.0+(d/s)**2)               # Cauchy weights
        A = np.c_[y,z,np.ones(len(y))]*w[:,None]; b=(y**2+z**2)*w
    return cy,cz,r,d

names={1:'rear RIGHT',2:'front RIGHT',3:'front LEFT',4:'rear LEFT'}
res={}
print(f"{'wheel':<12}{'n':>8}{'cY':>10}{'cZ':>9}{'R':>8}{'OD':>8}{'resid p90':>11}{'Xmin':>8}{'Xmax':>8}")
for i in (1,2,3,4):
    vi=np.unique(F[cc[i]].ravel()); P=V[vi]
    # outer tyre band only: exclude points near the wheel's inner/outer face extremes
    cy,cz,r,d = fit_circle(P[:,1],P[:,2])
    keep = d < np.percentile(d,70)           # keep the well-fitting tread band
    cy,cz,r,d2 = fit_circle(P[keep,1],P[keep,2])
    res[i]=(cy,cz,r,P[:,0].min(),P[:,0].max())
    print(f"{names[i]:<12}{len(P):>8}{cy:>10.1f}{cz:>9.1f}{r:>8.1f}{2*r:>8.1f}{np.percentile(d2,90):>11.2f}{P[:,0].min():>8.1f}{P[:,0].max():>8.1f}")

fY=(res[2][0]+res[3][0])/2; rY=(res[1][0]+res[4][0])/2
print(f"\nfront axle Y = {fY:.1f}   rear axle Y = {rY:.1f}")
print(f"WHEELBASE = {fY-rY:.1f} mm     (964 factory = 2272 mm)")
print(f"deviation = {fY-rY-2272:+.1f} mm  ({100*(fY-rY-2272)/2272:+.3f} %)")
print(f"\nmean tyre OD front {res[2][2]+res[3][2]:.1f} mm, rear {res[1][2]+res[4][2]:.1f} mm")
np.save('wheel_fits.npy', np.array([[res[i][0],res[i][1],res[i][2],res[i][3],res[i][4]] for i in (1,2,3,4)]))
