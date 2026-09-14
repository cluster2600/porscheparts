#!/usr/bin/env python3
"""Cinématique et dynamique simplifiée d'une distribution 4 soupapes sur 720°.

Étude de sensibilité, pas qualification. Aucune valeur de ce fichier n'est une
donnée M64 : chaque paramètre porte un statut (`assumed`, `sourced_reference`,
`repository_design_candidate`, `handbook_constant`) et une justification.

Conventions : angle vilebrequin phi en degrés, 0 = PMH de croisement
(fin échappement / début admission), cycle 0-720. Levées côté soupape.
Unités internes SI (m, kg, N, s, rad).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict, replace
import math

import numpy as np
from numpy.polynomial import Polynomial


def P(value, unit, status, justification):
    return {"value": value, "unit": unit, "status": status, "justification": justification}


FORBIDDEN_CLAIMS = ("valeur m64", "donnée m64", "cote m64", "mesuré sur m64", "valeur porsche")
ALLOWED_STATUS = {"assumed", "sourced_reference", "repository_design_candidate", "handbook_constant"}


# ---------------------------------------------------------------- paramètres
def default_valve(kind: str) -> dict:
    intake = kind == "intake"
    return {
        "max_lift_mm": P(11.5 if intake else 9.6, "mm", "repository_design_candidate",
                         "Levée candidate V2 du module four-valve-distribution (M64_PORTS_AND_CONTINUOUS_MOTION_20260907) ; pas une levée came M64."),
        "head_diameter_mm": P(40.0 if intake else 33.0, "mm", "sourced_reference",
                              "Fiche Swindon M64 24V (S2, interface-contract.json), benchmark non sélectionné."),
        "main_event_duration_crank_deg": P(240.0 if intake else 236.0, "deg", "assumed",
                                           "Durée de l'événement principal hors rampes, ordre de grandeur d'arbre sport route ; aucun profil M64 disponible."),
        "profile_fullness_c": P(1.2, "-", "assumed",
                                "Coefficient de la loi (1-u²)³(1+c u²) ; c=0 loi pointue, c<3 monotone. Choix de conception libre."),
        "ramp_height_mm": P(0.30, "mm", "assumed", "Hauteur de rampe de jeu typique 0,2-0,4 mm côté soupape ; non sourcée."),
        "ramp_duration_crank_deg": P(40.0, "deg", "assumed", "Durée de rampe de 30-50° vilebrequin, ordre de grandeur usuel ; non sourcée."),
        "centreline_crank_deg": P(105.0 if intake else 720.0 - 108.0, "deg", "assumed",
                                  "Centres de levée 105° après / 108° avant PMH de croisement ; calage non sourcé."),
        "lash_cold_mm": P(0.10 if intake else 0.15, "mm", "assumed",
                          "Jeu mécanique à froid supposé ; mettre 0 pour un rattrapage hydraulique. Le jeu M64 du manuel n'est pas qualifié dans le dépôt."),
        "lash_hot_delta_mm": P(-0.03 if intake else -0.05, "mm", "assumed",
                               "Variation froid→chaud supposée (signe et amplitude dépendent de la dilatation culasse/soupape, non modélisée)."),
        "valve_mass_kg": P(0.058 if intake else 0.050, "kg", "assumed",
                           "Soupape acier Ø40/Ø33, tige 6 mm, estimation volumique ; aucune pesée."),
        "retainer_keepers_mass_kg": P(0.013, "kg", "assumed", "Coupelle acier + demi-lunes, estimation ; aucune pesée."),
        "follower_equivalent_mass_kg": P(0.025, "kg", "assumed",
                                         "Masse ramenée à la soupape du poussoir/culbuteur (architecture de commande non choisie)."),
        "spring_wire_diameter_mm": P(3.8, "mm", "assumed", "Ressort simple hélicoïdal supposé ; aucune référence choisie."),
        "spring_mean_diameter_mm": P(22.0, "mm", "assumed", "Idem, compatible avec une tige 6 mm et une coupelle ~Ø28."),
        "spring_active_coils": P(5.0, "-", "assumed", "Idem."),
        "spring_inactive_coils": P(2.0, "-", "assumed", "Deux spires d'extrémité rapprochées meulées, convention usuelle."),
        "spring_installed_length_mm": P(40.0, "mm", "assumed", "Longueur montée supposée ; dépend du logement non conçu."),
        "spring_preload_N": P(300.0 if intake else 280.0, "N", "assumed", "Précharge montée supposée, ordre de grandeur sport."),
        "coil_bind_min_clearance_mm": P(1.0, "mm", "assumed", "Réserve minimale entre spires à levée max, règle de conception usuelle."),
        "spring_damping_ratio": P(0.05, "-", "assumed", "Amortissement équivalent du train ; non mesuré."),
        "contact_stiffness_N_per_mm": P(15000.0, "N/mm", "assumed",
                                        "Raideur de la chaîne came-poussoir-soupape ramenée à la soupape ; non mesurée."),
        "seat_stiffness_N_per_mm": P(50000.0, "N/mm", "assumed", "Raideur de contact siège-soupape ; non mesurée."),
        "piston_gap_at_tdc_closed_mm": P(6.0 if intake else 6.5, "mm", "assumed",
                                         "Distance axiale cylindre entre bord bas de soupape fermée et fond d'encoche piston au PMH ; géométrie piston non définie."),
        "required_piston_clearance_mm": P(1.5 if intake else 2.0, "mm", "assumed", "Jeu minimal piston-soupape de conception usuel."),
    }


def default_parameters() -> dict:
    return {
        "engine": {
            "crank_stroke_mm": P(76.4, "mm", "sourced_reference", "P3 Technical data, interface-contract.json (964 Turbo 3.6 / 993 Turbo S)."),
            "conrod_length_mm": P(127.0, "mm", "assumed", "Longueur de bielle non sourcée dans le dépôt ; valeur supposée."),
            "valve_axis_inclination_deg": P(8.0, "deg", "repository_design_candidate",
                                            "bank_inclination_deg de build_four_valve_distribution.Parameters ; candidat de conception."),
            "target_rpm": P(6500.0, "rpm", "assumed", "Scénario 3,6 L / 6 500 tr/min du dépôt, hypothèse (M64_RESEARCH_EXECUTION_20260912)."),
            "overrev_sweep_max_rpm": P(9500.0, "rpm", "assumed", "Borne de balayage surrégime, arbitraire."),
            "required_spring_margin": P(1.25, "-", "assumed", "Rapport effort ressort / inertie minimal visé, règle de conception usuelle."),
            "steel_shear_modulus_GPa": P(79.3, "GPa", "handbook_constant", "Module de cisaillement acier ressort, valeur de manuel."),
            "steel_density_kg_m3": P(7850.0, "kg/m3", "handbook_constant", "Masse volumique acier, valeur de manuel."),
            "separation_threshold_mm": P(0.05, "mm", "assumed", "Seuil d'indicateur de micro-décollement/rebond, arbitraire."),
            "gross_float_threshold_mm": P(0.5, "mm", "assumed", "Seuil d'affolement franc (décollement ou rebond), arbitraire."),
        },
        "intake": default_valve("intake"),
        "exhaust": default_valve("exhaust"),
    }


MANUAL_G15 = "catalog/manual/993-workshop-manual-group15-cylinder-head.json"


def stock_993_manual_parameters() -> dict:
    """Jeu `stock_993_manual` : défauts + calage d'origine 993 Carrera 2 soupapes (manuel p.16).

    N'écrase pas default_parameters(). Seuls les centres de levée et le jeu
    (hydraulique) sont remplacés ; levée, durées et ressort restent supposés.
    Référence d'origine 2V, pas une loi du 4 soupapes visé.
    """
    import copy
    params = copy.deepcopy(default_parameters())
    src = f"{MANUAL_G15} ; manuel 993 p.16, levée 1 mm jeu nul, 993 Carrera 2V (applicabilité au 4V non établie)."
    # admission : -1° (1° av. PMH) à 180+60 = 240° -> centre 119,5°
    params["intake"]["centreline_crank_deg"] = P(119.5, "deg", "sourced_reference",
                                                 "Milieu de AO 1° av. PMH / AF 60° ap. PMB ; " + src)
    # échappement : 540-45 = 495° à 720+6 = 726° -> centre 610,5°
    params["exhaust"]["centreline_crank_deg"] = P(610.5, "deg", "sourced_reference",
                                                  "Milieu de EO 45° av. PMB / EF 6° ap. PMH ; p.175 donne EF 2° (conflit non résolu) ; " + src)
    for kind in ("intake", "exhaust"):
        params[kind]["lash_cold_mm"] = P(0.0, "mm", "sourced_reference", "Rattrapage hydraulique (manuel 993 p.16, p.160) ; " + MANUAL_G15)
        params[kind]["lash_hot_delta_mm"] = P(0.0, "mm", "sourced_reference", "Jeu compensé par poussoir hydraulique, p.16 ; " + MANUAL_G15)
    ref = "Non utilisé dans le calcul ; " + src
    params["manual_reference"] = {
        "timing_1mm_inlet_opens_BTDC_deg": P(1, "deg", "sourced_reference", ref),
        "timing_1mm_inlet_closes_ABDC_deg": P(60, "deg", "sourced_reference", ref),
        "timing_1mm_exhaust_opens_BBDC_deg": P(45, "deg", "sourced_reference", ref),
        "timing_1mm_exhaust_closes_ATDC_deg": P(6, "deg", "sourced_reference", ref + " Conflit : p.175 = 2°."),
        "spring_installed_length_intake_mm": P(36.7, "mm", "sourced_reference", "A = 36,7 +0,3, double ressort, M64/05-08, p.157 ; " + MANUAL_G15),
        "spring_installed_length_exhaust_mm": P(35.7, "mm", "sourced_reference", "A = 35,7 +0,3, double ressort, M64/05-08, p.157 ; " + MANUAL_G15),
        "valve_stem_nominal_mm": P(7.97, "mm", "sourced_reference", "b = 7,970 -0,012, guide g 8,00-8,015, p.153/155 ; " + MANUAL_G15),
        "intake_head_diameter_2v_mm": P(49.0, "mm", "sourced_reference", "a = 49 ±0,1, 2V Carrera, p.155 ; " + MANUAL_G15),
        "exhaust_head_diameter_2v_mm": P(42.5, "mm", "sourced_reference", "a = 42,5 ±0,1, 2V Carrera, p.155 ; " + MANUAL_G15),
    }
    return params


def val(params: dict, *keys):
    node = params
    for key in keys:
        node = node[key]
    return node["value"]


def check_provenance(params: dict) -> list[str]:
    errors = []
    for group, entries in params.items():
        for name, entry in entries.items():
            if entry.get("status") not in ALLOWED_STATUS or not entry.get("justification"):
                errors.append(f"{group}.{name}")
            if entry.get("status") == "assumed" and any(s in entry["justification"].lower() for s in FORBIDDEN_CLAIMS):
                errors.append(f"{group}.{name}:assumed_presented_as_m64")
    return errors


# ------------------------------------------------------------------ loi came
U = Polynomial([1.0, 0.0, -1.0])  # 1 - u²


def main_poly(c: float) -> Polynomial:
    if not 0.0 <= c < 3.0:
        raise ValueError("profile_fullness_c_must_be_in_[0,3)")
    return U ** 3 * Polynomial([1.0, 0.0, c])


SMOOTH = Polynomial([0, 0, 0, 10, -15, 6])  # pas C2 : 10t³-15t⁴+6t⁵


@dataclass
class CamLaw:
    """Levée came ramenée à la soupape : C(phi) = h_r*rampe(phi) + L*f(u), C² partout."""

    max_lift_m: float
    main_duration_rad: float
    c: float
    ramp_height_m: float
    ramp_duration_rad: float
    centreline_rad: float
    lash_m: float

    @classmethod
    def from_params(cls, vp: dict, hot: bool = False) -> "CamLaw":
        lash = vp["lash_cold_mm"]["value"] + (vp["lash_hot_delta_mm"]["value"] if hot else 0.0)
        if lash < 0:
            raise ValueError("negative_lash")
        # amplitude principale choisie pour que la levée soupape max à froid égale max_lift_mm
        main = vp["max_lift_mm"]["value"] + vp["lash_cold_mm"]["value"] - vp["ramp_height_mm"]["value"]
        return cls(main * 1e-3, math.radians(vp["main_event_duration_crank_deg"]["value"]),
                   vp["profile_fullness_c"]["value"], vp["ramp_height_mm"]["value"] * 1e-3,
                   math.radians(vp["ramp_duration_crank_deg"]["value"]),
                   math.radians(vp["centreline_crank_deg"]["value"]), lash * 1e-3)

    @property
    def total_duration_rad(self):
        return self.main_duration_rad + 2 * self.ramp_duration_rad

    def cam_derivatives(self, phi_rad, order: int = 0):
        """Dérivée d'ordre `order` (0..3) de la levée came par rapport à phi (rad vilebrequin)."""
        phi = np.atleast_1d(np.asarray(phi_rad, dtype=float))
        x = np.mod(phi - self.centreline_rad + math.pi * 2, 4 * math.pi) - math.pi * 2  # relatif au centre, [-2π, 2π)
        half = self.main_duration_rad / 2
        out = np.zeros_like(x)
        # événement principal
        p = main_poly(self.c).deriv(order) if order else main_poly(self.c)
        u = x / half
        inside = np.abs(u) < 1
        out[inside] += self.max_lift_m * p(u[inside]) / half ** order
        # rampes : montée sur [-half-Dr, -half], plateau sur l'événement principal, descente symétrique
        dr = self.ramp_duration_rad
        s = SMOOTH.deriv(order) if order else SMOOTH
        t_up = (x + half + dr) / dr
        up = (t_up > 0) & (t_up < 1)
        out[up] += self.ramp_height_m * s(t_up[up]) / dr ** order
        t_dn = (half + dr - x) / dr
        dn = (t_dn > 0) & (t_dn < 1)
        out[dn] += self.ramp_height_m * s(t_dn[dn]) * (-1) ** order / dr ** order
        if order == 0:
            out[np.abs(x) <= half] += self.ramp_height_m
        return out

    def valve_lift(self, phi_rad):
        return np.maximum(self.cam_derivatives(phi_rad) - self.lash_m, 0.0)

    def valve_kinematics(self, phi_rad, rpm: float) -> dict:
        """Levée, vitesse, accélération, jerk soupape (suiveur en contact)."""
        w = rpm * 2 * math.pi / 60
        open_ = self.cam_derivatives(phi_rad) > self.lash_m
        return {"lift_m": self.valve_lift(phi_rad),
                "velocity_m_s": np.where(open_, self.cam_derivatives(phi_rad, 1) * w, 0.0),
                "acceleration_m_s2": np.where(open_, self.cam_derivatives(phi_rad, 2) * w ** 2, 0.0),
                "jerk_m_s3": np.where(open_, self.cam_derivatives(phi_rad, 3) * w ** 3, 0.0)}

    def open_close_events(self, rpm: float) -> dict:
        """Angles et vitesses d'ouverture/fermeture (croisement jeu) par bissection sur la rampe."""
        w = rpm * 2 * math.pi / 60
        half, dr = self.main_duration_rad / 2, self.ramp_duration_rad
        if self.lash_m >= self.ramp_height_m:
            return {"lash_within_ramp": False}
        f = lambda xx: float(self.cam_derivatives(self.centreline_rad + xx)[0]) - self.lash_m
        lo, hi = -half - dr, -half
        for _ in range(80):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if f(mid) < 0 else (lo, mid)
        xo = (lo + hi) / 2
        v_open = float(self.cam_derivatives(self.centreline_rad + xo, 1)[0]) * w
        return {"lash_within_ramp": True,
                "opening_crank_deg": math.degrees(self.centreline_rad + xo) % 720,
                "closing_crank_deg": math.degrees(self.centreline_rad - xo) % 720,
                "opening_velocity_m_s": v_open, "seating_velocity_m_s": -v_open}


# ------------------------------------------------------------------ ressort
def spring_properties(vp: dict, eng: dict) -> dict:
    G = eng["steel_shear_modulus_GPa"]["value"] * 1e9
    rho = eng["steel_density_kg_m3"]["value"]
    d = vp["spring_wire_diameter_mm"]["value"] * 1e-3
    D = vp["spring_mean_diameter_mm"]["value"] * 1e-3
    na = vp["spring_active_coils"]["value"]
    nt = na + vp["spring_inactive_coils"]["value"]
    k = G * d ** 4 / (8 * D ** 3 * na)
    mass = rho * math.pi * d ** 2 / 4 * math.pi * D * nt
    solid = nt * d
    installed = vp["spring_installed_length_mm"]["value"] * 1e-3
    lift = vp["max_lift_mm"]["value"] * 1e-3
    preload = vp["spring_preload_N"]["value"]
    f_max = preload + k * lift
    C = D / d
    wahl = (4 * C - 1) / (4 * C - 4) + 0.615 / C
    tau = lambda F: 8 * F * D * wahl / (math.pi * d ** 3)
    active_mass = rho * math.pi * d ** 2 / 4 * math.pi * D * na
    return {"rate_N_m": k, "mass_kg": mass, "solid_length_m": solid, "installed_length_m": installed,
            "preload_N": preload, "preload_deflection_m": preload / k,
            "free_length_m": installed + preload / k,
            "compressed_length_at_max_lift_m": installed - lift,
            "coil_bind_clearance_m": installed - lift - solid,
            "coil_bind_ok": installed - lift - solid >= vp["coil_bind_min_clearance_mm"]["value"] * 1e-3,
            "force_at_max_lift_N": f_max, "spring_index": C, "wahl_factor": wahl,
            "shear_stress_preload_MPa": tau(preload) / 1e6, "shear_stress_max_lift_MPa": tau(f_max) / 1e6,
            "surge_frequency_Hz": 0.5 * math.sqrt(k / active_mass)}


def effective_mass(vp: dict, spring: dict) -> float:
    return (vp["valve_mass_kg"]["value"] + vp["retainer_keepers_mass_kg"]["value"]
            + vp["follower_equivalent_mass_kg"]["value"] + spring["mass_kg"] / 3.0)


# ------------------------------------------------------ marge quasi statique
def spring_margin(law: CamLaw, spring: dict, m_eff: float, rpm: float, n: int = 7201) -> dict:
    """min F_ressort / (-m a) sur la zone de décélération (suiveur tiré par le ressort)."""
    phi = np.linspace(0, 4 * math.pi, n)
    kin = law.valve_kinematics(phi, rpm)
    a = kin["acceleration_m_s2"]
    neg = a < 0
    if not neg.any():
        return {"min_margin": math.inf}
    Fs = spring["preload_N"] + spring["rate_N_m"] * kin["lift_m"][neg]
    ratio = Fs / (-m_eff * a[neg])
    i = int(np.argmin(ratio))
    return {"min_margin": float(ratio[i]), "crank_deg": math.degrees(phi[neg][i]),
            "lift_mm": float(kin["lift_m"][neg][i] * 1e3)}


def float_rpm_quasistatic(law, spring, m_eff, rpm_ref=1000.0, required=1.0) -> float:
    """La marge varie en 1/N² : N_lim = N_ref sqrt(marge_ref / requis)."""
    return rpm_ref * math.sqrt(spring_margin(law, spring, m_eff, rpm_ref)["min_margin"] / required)


# --------------------------------------------------------- piston-soupape
def piston_drop(phi_rad, stroke_m, rod_m):
    """Distance du piston sous le PMH (bielle-manivelle exacte)."""
    r = stroke_m / 2
    phi = np.asarray(phi_rad, dtype=float)
    return r * (1 - np.cos(phi)) + rod_m - np.sqrt(rod_m ** 2 - (r * np.sin(phi)) ** 2)


def piston_valve_gap(phi_rad, valve_lift_m, vp, eng, extra_advance_deg=0.0):
    """Jeu axial cylindre = d0 + chute piston - levée·cos(inclinaison). Géométrie simplifiée."""
    d0 = vp["piston_gap_at_tdc_closed_mm"]["value"] * 1e-3
    alpha = math.radians(eng["valve_axis_inclination_deg"]["value"])
    s = piston_drop(phi_rad, eng["crank_stroke_mm"]["value"] * 1e-3, eng["conrod_length_mm"]["value"] * 1e-3)
    return d0 + s - valve_lift_m * math.cos(alpha)


def interference(law, vp, eng, advance_deg=0.0, n=7201, lift_override=None, phi=None):
    if phi is None:
        phi = np.linspace(0, 4 * math.pi, n)
    shifted = replace(law, centreline_rad=law.centreline_rad - math.radians(advance_deg))
    lift = shifted.valve_lift(phi) if lift_override is None else lift_override
    gap = piston_valve_gap(phi, lift, vp, eng)
    i = int(np.argmin(gap))
    req = vp["required_piston_clearance_mm"]["value"] * 1e-3
    return {"advance_deg": advance_deg, "min_gap_mm": float(gap[i] * 1e3), "crank_deg": math.degrees(phi[i]),
            "contact": bool(gap[i] <= 0), "below_required": bool(gap[i] < req)}


# ------------------------------------------------------------- modèle 1-ddl
def simulate_sdof(law: CamLaw, vp: dict, spring: dict, m_eff: float, rpm: float, cycles: int = 3,
                  steps_per_cycle: int = 14400) -> dict:
    """Masse m (soupape équivalente), ressort précontraint, contact unilatéral came et siège.

    m x'' = -k (x + x0) - c x' + kc <y - x>+ + ks <-x>+ - cs x' [x<0]
    y = levée commandée (came - jeu). Intégration RK4 à pas fixe (contacts non lisses).
    """
    w = rpm * 2 * math.pi / 60
    k, x0 = spring["rate_N_m"], spring["preload_deflection_m"]
    kc = vp["contact_stiffness_N_per_mm"]["value"] * 1e3
    ks = vp["seat_stiffness_N_per_mm"]["value"] * 1e3
    zeta = vp["spring_damping_ratio"]["value"]
    c = 2 * zeta * math.sqrt(k * m_eff)
    cs = 2 * 0.3 * math.sqrt(ks * m_eff)
    cc = 2 * zeta * math.sqrt(kc * m_eff)
    T = 4 * math.pi / w
    n = cycles * steps_per_cycle
    h = T / steps_per_cycle
    # levée commandée échantillonnée aux demi-pas
    t_all = np.arange(2 * n + 1) * h / 2
    y_all = law.cam_derivatives(w * t_all) - law.lash_m
    yd_all = law.cam_derivatives(w * t_all, 1) * w

    def acc(x, v, j):
        gap = y_all[j] - x
        fc = kc * gap + cc * (yd_all[j] - v) if gap > 0 else 0.0
        fc = max(fc, 0.0)
        fs = (ks * (-x) - cs * v) if x < 0 else 0.0
        fs = max(fs, 0.0)
        return (-k * (x + x0) - c * v + fc + fs) / m_eff, fc

    x = -k * x0 / ks
    v = 0.0
    xs = np.empty(n + 1); fcs = np.empty(n + 1); ys = y_all[::2]
    xs[0] = x; fcs[0] = acc(x, v, 0)[1]
    for i in range(n):
        j = 2 * i
        a1, _ = acc(x, v, j)
        a2, _ = acc(x + h / 2 * v, v + h / 2 * a1, j + 1)
        a3, _ = acc(x + h / 2 * (v + h / 2 * a1), v + h / 2 * a2, j + 1)
        a4, _ = acc(x + h * (v + h / 2 * a2), v + h * a3, j + 2)
        x, v = x + h / 6 * (v + 2 * (v + h / 2 * a1) + 2 * (v + h / 2 * a2) + (v + h * a3)), v + h / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        xs[i + 1] = x; fcs[i + 1] = acc(x, v, j + 2)[1]
    last = slice((cycles - 1) * steps_per_cycle, n + 1)
    x_l, y_l, fc_l = xs[last], ys[last], fcs[last]
    commanded_open = y_l > 0
    separation = np.where(commanded_open, x_l - y_l, 0.0)
    # rebond : levée soupape positive alors que la came est refermée (y<=0), hors fin de fermeture immédiate
    bounce = np.where(~commanded_open, x_l, 0.0)
    loss = commanded_open & (fc_l <= 0) & (y_l > 1e-4)
    return {"rpm": rpm, "max_separation_mm": float(max(separation.max(), 0) * 1e3),
            "max_bounce_mm": float(max(bounce.max(), 0) * 1e3),
            "contact_loss_fraction_of_open": float(loss.sum() / max(commanded_open.sum(), 1)),
            "phi_deg": np.degrees(w * t_all[::2][last] % (4 * math.pi)), "x_m": x_l, "y_m": y_l}


def free_oscillation(m, k, x_init, t_end, steps):
    """Cas limite harmonique pour le test : x'' = -k/m x, RK4 identique."""
    h = t_end / steps
    x, v = x_init, 0.0
    out = [x]
    for _ in range(steps):
        f = lambda xx: -k / m * xx
        a1 = f(x); a2 = f(x + h / 2 * v); a3 = f(x + h / 2 * (v + h / 2 * a1)); a4 = f(x + h * (v + h / 2 * a2))
        x, v = x + h / 6 * (v + 2 * (v + h / 2 * a1) + 2 * (v + h / 2 * a2) + (v + h * a3)), v + h / 6 * (a1 + 2 * a2 + 2 * a3 + a4)
        out.append(x)
    return np.array(out), v
