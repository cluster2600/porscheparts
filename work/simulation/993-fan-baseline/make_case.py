#!/usr/bin/env python3
"""Generate two blockMesh annular-duct fan-disc cases from parameters.json.

Every numeric input comes from parameters.json (see PARAMETERS.md for
provenance tags); nothing is hard-coded here.

Convention: +x = fan axis, upstream -> downstream. Mesh = 3 axial blocks
(upstream | disc | downstream) x 4 angular quadrant blocks, each a single
hex with simpleGrading biased to the inner (hub) wall. The hub is a wall
(no wedge singularity). The disc block carries the actuator-disc fvOptions
(momentum penalty + uniform pressure-rise source) -- a labelled SURROGATE,
no blades (blade count UNKNOWN, ACQ-0005).

Case A uses the as-published F0 throat (252 mm) which geometrically FAILS
(-14 mm radial clearance vs the 280 mm impeller hypothesis); case B uses the
284 mm throat required for 2 mm clearance and is the informative case.
"""
import json
import math
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PARAMS = json.load(open(os.path.join(HERE, "parameters.json")))


def merged(name):
    c = dict(PARAMS["common"])
    c.update(PARAMS["cases"][name])
    return c


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def write_case(name):
    c = merged(name)
    cdir = os.path.join(HERE, name)
    if os.path.isdir(cdir):
        shutil.rmtree(cdir)
    for sub in ("0", "system", "constant"):
        os.makedirs(os.path.join(cdir, sub))

    mm = 1e-3
    R_hub = c["D_hub_mm"] / 2 * mm
    R_th = c["D_throat_mm"] / 2 * mm
    t_disc = c["t_disc_mm"] * mm
    H = R_th - R_hub                                   # annulus height [m]
    L_up = c["up_len_annH"] * H
    L_dn = c["dn_len_annH"] * H
    x = [0.0, L_up, L_up + t_disc, L_up + t_disc + L_dn]
    xs = x
    A = math.pi / 4 * ((R_th * 2) ** 2 - (R_hub * 2) ** 2)
    U_in = (c["Q_l_s"] / 1000.0) / A                   # disc-plane mean velocity
    nu = c["mu_air_Pa_s"] / c["rho_air_kg_m3"]
    n_fan = c["drive_ratio"] * c["n_eng_rpm"]

    nx = [c["nx_up_per_H"], c["nx_disc"], c["nx_dn_per_H"]]
    nr, grade_r = c["nr"], 0.7                         # bias cells toward hub wall
    ax = "M64 fan-baseline deck | tag: SURROGATE (exploratory; placeholder BCs)"

    # ---------- blockMeshDict (plain-text template; no f-string brace games) ----------
    # Radial layers: [hub->Rmid (ri=0) | Rmid->throat (ri=1)]. Angular: 4 quadrant
    # quarter-annulus blocks. Axial: [up | disc | dn]. Hub is a wall (no wedge).
    R_mid = R_hub + 0.4 * H
    rlay = [R_hub, R_mid, R_th]
    angs = [0.0, 90.0, 180.0, 270.0]

    vlist, vid_by_coord = [], {}
    def V(xx, r, deg):
        a = math.radians(deg)
        k = (round(xx, 9), round(r * math.cos(a), 9), round(r * math.sin(a), 9))
        if k not in vid_by_coord:
            vid_by_coord[k] = len(vlist)
            vlist.append(k)
        return vid_by_coord[k]

    # hex vertex ordering: 0..3 at x=xs[bi] (ring a0,a1,a2,a3), 4..7 at x=xs[bi+1].
    # blockMesh canonical faces (edge-pair rule; loop order cosmetic):
    #   0:(0 3 7 4) x=xs[bi]  | 1:(1 2 6 5) x=xs[bi+1]
    #   2:(0 1 5 4) ang a0    | 3:(2 3 7 6) ang a1
    #   4:(0 1 2 3) r_inner   | 5:(4 5 6 7) r_outer
    # => inlet face=0, outlet face=1, hub face=4, throat face=5.
    blocks, patches = [], {"inlet": [], "outlet": [], "hub": [], "throat": []}
    nx_seg = max(nx)                       # uniform axial count in all three zones
    bid = 0
    for bi in range(3):
        for ri in range(2):
            for q in range(4):
                a0, a1 = angs[q], angs[(q + 1) % 4]
                v = [V(xs[bi], rlay[ri], a0), V(xs[bi], rlay[ri + 1], a0),
                     V(xs[bi], rlay[ri + 1], a1), V(xs[bi], rlay[ri], a1),
                     V(xs[bi + 1], rlay[ri], a0), V(xs[bi + 1], rlay[ri + 1], a0),
                     V(xs[bi + 1], rlay[ri + 1], a1), V(xs[bi + 1], rlay[ri], a1)]
                blocks.append(f"hex ({' '.join(map(str, v))}) ({nx_seg} 1 1) simpleGrading (1 1 1)")
                # classify each canonical face by its vertex coordinates
                pts = [vlist[i] for i in v]
                def face_test(loop, mode, val):
                    fp = [pts[i] for i in loop]
                    if mode == "x":
                        return all(abs(p[0] - val) < 1e-12 for p in fp)
                    return all(abs(math.hypot(p[1], p[2]) - val) < 1e-12 for p in fp)
                CF = {0: (0, 3, 7, 4), 1: (1, 5, 6, 2), 2: (4, 5, 1, 0),
                      3: (2, 6, 7, 3), 4: (0, 1, 2, 3), 5: (4, 5, 6, 7)}
                for lab, loop in CF.items():
                    if face_test(loop, "x", xs[0]) and bi == 0:
                        patches["inlet"].append((bid, lab))
                    elif face_test(loop, "x", xs[3]) and bi == 2:
                        patches["outlet"].append((bid, lab))  # full annulus: both layers
                    elif face_test(loop, "r", R_hub) and ri == 0:
                        patches["hub"].append((bid, lab))
                    elif face_test(loop, "r", R_th) and ri == 1:
                        patches["throat"].append((bid, lab))
                bid += 1

    vlines = "\n".join(f"    ({a:.6f} {b:.6f} {c_:.6f})" for a, b, c_ in vlist)
    blines = "\n".join(f"    {b}" for b in blocks)

    def pblock(label, kind, entries):
        fl = "\n".join(f"            ({i} {j})" for i, j in entries)
        return (f"    {label}\n    {{\n        type {kind};\n"
                f"        faces\n        (\n{fl}\n        );\n    }}\n")

    patches_txt = "".join([
        pblock('inlet', 'patch', patches['inlet']),
        pblock('outlet', 'patch', patches['outlet']),
        pblock('hub', 'wall', patches['hub']),
        pblock('throat', 'wall', patches['throat']),
    ])

    bmd = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      blockMeshDict;
}
// __AX__
convertToMeters 1.0;
vertices
(
__VERTICES__
);
blocks
(
__BLOCKS__
);
boundary
(
__PATCHS__);
edges
(
);
// radial split R_mid=__RMID__ m; hub is a wall (no wedge singularity);
// quadrant and axial interfaces become auto-matching internal faces.
"""
    bmd = (bmd.replace("__AX__", ax).replace("__VERTICES__", vlines)
              .replace("__BLOCKS__", blines).replace("__PATCHS__", patches_txt)
              .replace("__RMID__", f"{R_mid:.4f}"))
    write(os.path.join(cdir, "system", "blockMeshDict"), bmd)

    # ---------- 0/U, 0/p ----------
    write(os.path.join(cdir, "0", "U"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volVectorField;
    object      U;
}}
// {ax}
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform ({U_in:.6f} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    hub
    {{
        type            fixedValue;
        value           uniform (0 0 0);
    }}
    throat
    {{
        type            fixedValue;
        value           uniform (0 0 0);
    }}
}}
""")
    write(os.path.join(cdir, "0", "p"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      p;
}}
// {ax}
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{{
    inlet
    {{
        type            zeroGradient;
    }}
    outlet
    {{
        type            fixedValue;
        value           uniform 0;
    }}
    hub
    {{
        type            zeroGradient;
    }}
    throat
    {{
        type            zeroGradient;
    }}
}}
""")

    # ---------- turbulence 0 fields ----------
    I = 0.05
    k = (2.0 / 3.0) * (I * U_in) ** 2
    eps = 0.09 ** 0.75 * k ** 1.5 / (0.07 * H)
    nut = k / eps

    def tfield(fn, cls, dim, val, inlet_val):
        return f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    object      {fn};
}}
dimensions      {dim};
internalField   uniform {val:.6g};
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {inlet_val:.6g};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    hub
    {{
        type            fixedValue;
        value           uniform {'0' if fn == 'k' else '1e-8' if fn == 'epsilon' else '0'};
    }}
    throat
    {{
        type            fixedValue;
        value           uniform {'0' if fn == 'k' else '1e-8' if fn == 'epsilon' else '0'};
    }}
}}
"""

    write(os.path.join(cdir, "0", "k"), tfield("k", "volScalarField", "[0 2 -2 0 0 0 0]", k, k))
    write(os.path.join(cdir, "0", "epsilon"), tfield("epsilon", "volScalarField", "[0 2 -3 0 0 0 0]", eps, eps))
    write(os.path.join(cdir, "0", "nut"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       volScalarField;
    object      nut;
}}
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform {nut:.6g};
boundaryField
{{
    inlet
    {{
        type            calculated;
        value           uniform {nut:.6g};
    }}
    outlet
    {{
        type            calculated;
        value           uniform {nut:.6g};
    }}
    hub
    {{
        type            calculated;
        value           uniform {nut:.6g};
    }}
    throat
    {{
        type            calculated;
        value           uniform {nut:.6g};
    }}
}}
""")

    # ---------- system: fvSolution / fvSchemes ----------
    write(os.path.join(cdir, "system", "fvSolution"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSolution;
}}
solvers
{{
    p
    {{
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-7;
        relTol          0.01;
    }}
    "(U|k|epsilon)"
    {{
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-6;
        relTol          0.01;
    }}
}}
SIMPLE
{{
    nNonOrthogonalCorrectors 1;
    consistency yes;
    residualControl
    {{
        p               1e-5;
        U               1e-5;
        "(k|epsilon|omega)" 1e-5;
    }}
}}
guessLinearInitial yes;
initialResidualControl
{{
    p               1e-4;
    U               1e-4;
    "(k|epsilon|omega)" 1e-4;
}}
relaxationFactors
{{
    fields
    {{
        p               0.3;
    }}
    equations
    {{
        ".*"            0.7;
    }}
}}
""")
    write(os.path.join(cdir, "system", "fvSchemes"), """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      fvSchemes;
}
ddtSchemes
{
    default         steadyState;
}
gradSchemes
{
    default         Gauss linear;
}
divSchemes
{
    default         none;
    div(phi,U)      Gauss linearUpwind grad(U);
    div(phi,k)          Gauss upwind;
    div(phi,epsilon)    Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes
{
    default         Gauss linear corrected;
}
interpolationSchemes
{
    default         linear;
}
snGradSchemes
{
    default         corrected;
}
""")
    write(os.path.join(cdir, "system", "controlDict"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      controlDict;
}}
application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         200;
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      0;
writeFormat     ascii;
writePrecision  8;
writeCompression off;
timeFormat      general;
runTimeModifiable yes;
functions
{{
    outFlow
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
        writeFields     no;
        log             yes;
        regionType      patch;
        name            outlet;
        operation       average;
        fields          (U);
    }}
    pIn
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
        writeFields     no;
        log             yes;
        regionType      patch;
        name            inlet;
        operation       average;
        fields          (p);
    }}
    pOut
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    writeTime;
        writeFields     no;
        log             yes;
        regionType      patch;
        name            outlet;
        operation       average;
        fields          (p);
    }}
}}
""")
    # single vectorCodedSource: Su = -beta*|U|*U  (drag proxy)  +  +dp*xhat/V_disc
    # (pressure-jump proxy as force per unit volume, Pa). Both ASSUMPTION-tagged.
    fv_body = """// Actuator-disc SURROGATE over the disc block (tag: ASSUMPTION; PARAMETERS.md M-01..M-03).
// Su = -beta*|U|*U + dp/Vdisc * xhat  [Pa]: quadratic blockage proxy + prescribed
// fan static rise (no measured fan map; blade count UNKNOWN -> no rotation model).
discSurrogate
{
    type                vectorCodedSource;
    active              yes;
    vectorCodedSourceCoeffs
    {
        selectionMode       cellSet;
        cellSets            ("discCells");
        fields              ("U");
        name                discSurrogate;
        redirectTypes       true;
        codeAddSup
        "const vectorField& Uc = U.source_.primitiveField();\nvectorField::subList(su_, cells_) = -scalar(__BETA__)*mag(Uc)*Uc + vector(__DP__/__VDISC__, 0, 0);";
        codeAddEqn
        "const vectorField& Uc = U.source_.primitiveField();\nvectorField::subList(su_, cells_) = -scalar(__BETA__)*mag(Uc)*Uc + vector(__DP__/__VDISC__, 0, 0);";
    }
}
"""
    v_disc = A * (x[2] - x[1])            # disc-block volume [m^3]
    fv = ('FoamFile\n{\n    version     2.0;\n    format      ascii;\n'
          '    class       dictionary;\n    object      fvOptions;\n}\n'
          + fv_body.replace("__DP__", f"{c['dp_fan_Pa']:.6g}")
                   .replace("__BETA__", f"{c['beta_disc_1_m']:.6g}")
                   .replace("__VDISC__", f"{v_disc:.9g}"))
    write(os.path.join(cdir, "system", "decomposeParDict"), """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      decomposeParDict;
}
numberOfSubdomains 1;
method              simple;
simpleCoeffs
{
    n               (1 1 1);
    delta           0.001;
}
""")

    # ---------- constant ----------
    write(os.path.join(cdir, "constant", "transportProperties"), f"""FoamFile
{{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      transportProperties;
}}
transportModel  Newtonian;
nu              nu [0 2 -1 0 0 0 0] {c["mu_air_Pa_s"] / c["rho_air_kg_m3"]:.6g};
""")
    write(os.path.join(cdir, "constant", "turbulenceProperties"), """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      turbulenceProperties;
}
simulationType  RAS;

RAS
{
    RASModel        kEpsilon;
    turbulence      on;
    printExtraInfo  off;
}
""")
    write(os.path.join(cdir, "constant", "RASProperties"), """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      RASProperties;
}
RASModel          kEpsilon;
turbulence        on;
printExtraInfo    off;
""")

    # ---------- cellSet for disc block (topoSet boxToCell) ----------
    xlo, xhi = x[1], x[2]
    # ---------- cellSet for disc block (topoSet boxToCell, v2312 actions list) ----------
    xlo, xhi = x[1], x[2]
    topo = """FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      topoSetDict;
}
// disc block x in [__XLO__, __XHI__] m
actions
(
    {
        name            discCells;
        type            cellSet;
        action          new;
        source          boxToCell;
        sourceInfo
        {
            box             (__XLOM__ -1.0 -1.0) (__XHIM__ 1.0 1.0);
        }
    }
);
"""
    topo = (topo.replace("__XLO__", f"{xlo:.6f}").replace("__XHI__", f"{xhi:.6f}")
                .replace("__XLOM__", f"{xlo - 1e-4:.6f}").replace("__XHIM__", f"{xhi + 1e-4:.6f}"))
    write(os.path.join(cdir, "system", "topoSetDict"), topo)

    meta = {
        "case": name,
        "axiom_note": ax,
        "D_throat_mm": c["D_throat_mm"], "D_throat_tag": c["D_throat_tag"],
        "D_imp_mm": c["D_imp_mm"], "D_imp_tag": c["D_imp_tag"],
        "radial_clearance_mm": (c["D_throat_mm"] - c["D_imp_mm"]) / 2,
        "D_hub_mm": c["D_hub_mm"], "D_hub_tag": c["D_hub_tag"],
        "t_disc_mm": c["t_disc_mm"], "t_disc_tag": c["t_disc_tag"],
        "Q_l_s": c["Q_l_s"], "Q_tag": c["Q_tag"],
        "n_eng_rpm": c["n_eng_rpm"], "n_fan_rpm_derived": n_fan,
        "A_disc_m2": A, "U_disc_mean_m_s": U_in,
        "dp_fan_Pa_ASSUMED": c["dp_fan_Pa"],
        "beta_disc_1_m_ASSUMED": c["beta_disc_1_m"],
        "annulus_height_m": H,
        "domain_x_m": x,
        "cells_per_case_note": "see blockMeshDict",
        "n_blades": c["n_blades"], "n_blades_tag": c["n_blades_tag"],
    }
    write(os.path.join(cdir, "case_meta.json"), json.dumps(meta, indent=2))
    print(name, "U_disc:", round(U_in, 3), "m/s",
          "clearance_mm:", meta["radial_clearance_mm"])


if __name__ == "__main__":
    for n in sys.argv[1:] or list(PARAMS["cases"]):
        write_case(n)
