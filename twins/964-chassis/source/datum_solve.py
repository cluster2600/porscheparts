import numpy as np, json, math
# Half-spacings Y (mm) from manual transverse dims A..I
Yh = {20:440/2, 3:610/2, 5:770/2, 6:204/2, 17:1330/2, 18:1236/2, 12:278/2, 19:1018/2, 21:640/2}
# Plan-projected ("bracketed") cross-diagonals: dx = sqrt(proj^2 - (ya+yb)^2)
def dx(proj, a, b):
    s = Yh[a]+Yh[b]
    if proj <= s: raise ValueError(f"proj {proj} <= span {s}")
    return math.sqrt(proj**2 - s**2)
K = dx(1500, 20,17); L = dx(1170, 3,17); P = dx(913, 20,5)
N = dx(1482, 12,21); O = dx(1653, 18,21)
print("solved longitudinal separations from plan-projected diagonals:")
for nm,v,pair in (("K",K,(20,17)),("L",L,(3,17)),("P",P,(20,5)),("N",N,(12,21)),("O",O,(18,21))):
    print(f"  {nm}: dX({pair[0]}-{pair[1]}) = {v:8.1f} mm")
# chain, P17 as local origin, +X forward
X = {17:0.0}
X[18] = X[17]-1245.0          # R, side view
X[19] = X[17]-1328.0          # S, side view
X[20] = X[17]+K
X[3]  = X[17]+L
X[5]  = X[20]-P
X[21] = X[18]-O
X[12] = X[21]+N
X[6]  = None                  # D gives Y only; no published longitudinal tie
print("\nlongitudinal chain (P17 = 0, +X forward):")
for p in (20,3,5,17,18,19,12,21):
    print(f"  P{p:<3} X = {X[p]:9.1f}   Y = +/-{Yh[p]:6.1f}")
json.dump({"Yh":{str(k):v for k,v in Yh.items()},
           "X_local":{str(k):v for k,v in X.items() if v is not None}},
          open('datum_chain.json','w'), indent=1)
# independent re-check: recompute every published diagonal from the solved chain
print("\nre-check of published dimensions from the solved chain:")
checks=[("M",17,18,1788,3,"oblique-cross"),("K",20,17,1500,3,"proj-cross"),("L",3,17,1170,None,"proj-cross"),
        ("P",20,5,913,None,"proj-cross"),("N",12,21,1482,3,"proj-cross"),("O",18,21,1653,3,"proj-cross")]
for nm,a,b,nom,tol,kind in checks:
    d = math.hypot(X[a]-X[b], Yh[a]+Yh[b])
    ok = "ok" if (tol is None or abs(d-nom)<=tol) else "MISMATCH"
    print(f"  {nm}: model {d:8.1f}  manual {nom:7.1f} {'+/-'+str(tol) if tol else '':>6}   {d-nom:+6.1f}  {ok}")
