"""Quasi-isotropic in-plane properties of a laminate, from unidirectional lamina data.

A quasi-isotropic stack ([0/+45/-45/90]s and friends) has an in-plane stiffness
matrix A that is isotropic. Its equivalent engineering constants follow from the
laminate invariants U1, U4, U5, so the shell FE model can stay isotropic and the
only inputs are the UD lamina constants. Bending is NOT isotropic and is not
covered here: see the caveats in README.md.

Units: MPa, g/cm3.
"""
import numpy as np

# UD lamina properties, epoxy matrix, fibre volume fraction ~0.55-0.60.
# Textbook / datasheet class values, evidence level D. Not supplier-certified.
LAMINA = {
    # E1, E2, G12, nu12, rho
    "carbon": dict(E1=135000.0, E2=10000.0, G12=5000.0, nu12=0.30, rho=1.60),
    "aramid": dict(E1= 76000.0, E2= 5500.0, G12=2200.0, nu12=0.34, rho=1.38),
}
STEEL = dict(E=210000.0, nu=0.30, rho=7.85)


def reduced_stiffness(E1, E2, G12, nu12, **_):
    """Plane-stress reduced stiffness Q of a UD lamina, in its own axes."""
    nu21 = nu12 * E2 / E1
    d = 1.0 - nu12 * nu21
    return np.array([[E1 / d, nu12 * E2 / d, 0.0],
                     [nu12 * E2 / d, E2 / d, 0.0],
                     [0.0, 0.0, G12]])


def quasi_isotropic(Q):
    """Equivalent isotropic in-plane E, nu, G of a quasi-isotropic stack of lamina Q."""
    Q11, Q22, Q12, Q66 = Q[0, 0], Q[1, 1], Q[0, 1], Q[2, 2]
    U1 = (3 * Q11 + 3 * Q22 + 2 * Q12 + 4 * Q66) / 8.0
    U4 = (Q11 + Q22 + 6 * Q12 - 4 * Q66) / 8.0
    U5 = (U1 - U4) / 2.0
    return dict(E=(U1 ** 2 - U4 ** 2) / U1, nu=U4 / U1, G=U5)


def hybrid(carbon_ply_fraction):
    """Carbon/aramid hybrid, quasi-isotropic. Ply-fraction mixing of Q is exact for A."""
    f = float(carbon_ply_fraction)
    if not 0.0 <= f <= 1.0:
        raise ValueError("carbon_ply_fraction must be in [0, 1]")
    Q = f * reduced_stiffness(**LAMINA["carbon"]) + (1 - f) * reduced_stiffness(**LAMINA["aramid"])
    out = quasi_isotropic(Q)
    out["rho"] = f * LAMINA["carbon"]["rho"] + (1 - f) * LAMINA["aramid"]["rho"]
    out["carbon_ply_fraction"] = f
    return out


if __name__ == "__main__":
    # Self-check: a QI stack of an ISOTROPIC lamina must return that same isotropic material.
    E, nu = 70000.0, 0.33
    iso = quasi_isotropic(reduced_stiffness(E, E, E / (2 * (1 + nu)), nu))
    assert abs(iso["E"] - E) < 1e-6 and abs(iso["nu"] - nu) < 1e-9, iso
    print(f"self-check ok: QI of isotropic lamina returns E={iso['E']:.1f} nu={iso['nu']:.3f}\n")
    print(f"{'laminate':<24}{'E (MPa)':>10}{'nu':>7}{'G (MPa)':>10}{'rho':>7}")
    for name, f in (("carbone QI", 1.0), ("hybride 50/50 QI", 0.5), ("aramide QI", 0.0)):
        m = hybrid(f)
        print(f"{name:<24}{m['E']:10.0f}{m['nu']:7.3f}{m['G']:10.0f}{m['rho']:7.2f}")
    print(f"{'acier':<24}{STEEL['E']:10.0f}{STEEL['nu']:7.3f}"
          f"{STEEL['E']/(2*(1+STEEL['nu'])):10.0f}{STEEL['rho']:7.2f}")
