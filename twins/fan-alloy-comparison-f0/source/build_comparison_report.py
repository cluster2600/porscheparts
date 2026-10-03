#!/usr/bin/env python3
"""Generate a reproducible comparison from completed solves, not from invented results."""
import argparse
import csv
import json
import math
from pathlib import Path

from compare_alloys import load_cards, modal_results, sha, static_results, scale_factors


def build(run, cards_path, output, runtime="See per-case solver version and execution record"):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from pxr import Gf, Usd, UsdGeom
    import trimesh

    cards = load_cards(cards_path)
    prep = json.loads((run/"993-cases/preparation.json").read_text())
    if prep["material_cards_sha256"] != sha(cards_path):
        raise ValueError("Material cards changed after solve preparation")
    if prep["cases"][0]["rpm"] != 10000.:
        raise ValueError("Report expects a 10000 rpm baseline")
    properties = np.load(run/"993-reference-properties.npz")
    mesh = trimesh.load(run/"993-reference-review-mm.stl",process=True)
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume <= 0:
        raise ValueError("Mass and inertia require a closed consistently oriented positive solid")
    volume = float(properties["volume"])
    if not math.isclose(volume,mesh.volume,rel_tol=1e-7):
        raise ValueError("Cached geometry properties do not match input mesh")
    if not np.allclose(properties["inertia"],mesh.moment_inertia,rtol=1e-7):
        raise ValueError("Cached inertia mismatch")
    output.mkdir(parents=True,exist_ok=False)
    cases=[]; rows=[]
    base_modes=modal_results(run/"993-cases/alsi10mg",prep["cases"][0]["modal_deck_sha256"])
    for card,record in zip(cards["materials"],prep["cases"]):
        if record["material_card"] != card:
            raise ValueError("Case material mismatch")
        solved=static_results(run/"993-cases"/card["id"],record["rotor_deck_sha256"])
        rho=card["density_g_cm3"]
        factors=scale_factors(rho,card["young_modulus_GPa"],10000.)
        mass=volume*rho*1e-6
        inertia=float(properties["inertia"][2,2])*rho*1e-12
        case={"id":card["id"],"material":card,"mass_kg":mass,"polar_inertia_kg_m2":inertia,
              "static_10000rpm":solved,
              "modes_hz":[f*factors["unprestressed_frequency"] for f in base_modes],
              "modal_method":"fresh CalculiX solve" if card["id"]=="alsi10mg" else "exact elastic similarity, common Poisson ratio, same mesh and restraints",
              "static_deck_sha256":record["rotor_deck_sha256"],
              "mass_vs_aluminium_fraction":rho/2.67}
        cases.append(case)
        for rpm in (3000.,6000.,8500.,10000.,12000.):
            w=(rpm/10000.)**2; sigma=solved["von_mises_max_MPa"]*w
            y=card["tensile_yield_comparator_MPa"]
            rows.append({"material":card["id"],"rpm_rotor":rpm,"mass_kg":mass,
                         "polar_inertia_kg_m2":inertia,"peak_von_mises_MPa":sigma,
                         "maximum_displacement_mm":solved["maximum_displacement_mm"]*w,
                         "rotation_frequency_hz":rpm/60.,"blade_passage_frequency_hz_11_blades":11*rpm/60.,
                         "kinetic_energy_J":.5*inertia*(rpm*math.pi/30.)**2,
                         "tip_speed_m_s":.1225*rpm*math.pi/30.,
                         "yield_comparator_over_peak":None if y is None else y/sigma,
                         "linear_result_above_yield_comparator":None if y is None else sigma>y,
                         "method":"fresh static solve" if rpm==10000. else "elastic omega_squared extrapolation"})
    ref=cases[0]["static_10000rpm"]
    similarity_errors={}
    for case in cases[1:]:
        f=scale_factors(case["material"]["density_g_cm3"],case["material"]["young_modulus_GPa"],10000.)
        stress_error=abs(case["static_10000rpm"]["von_mises_max_MPa"]/(ref["von_mises_max_MPa"]*f["centrifugal_stress"])-1)
        disp_error=abs(case["static_10000rpm"]["maximum_displacement_mm"]/(ref["maximum_displacement_mm"]*f["centrifugal_displacement"])-1)
        if max(stress_error,disp_error)>1e-4:
            raise ValueError("Independent material solves fail density/modulus similarity check")
        similarity_errors[case["id"]]={"stress_relative_error":stress_error,"displacement_relative_error":disp_error}
    scan_receipts={}
    for name in ("935-voxel-0p65","935-voxel-0p40","935-voxel-inverted-0p65","993-voxel-witness"):
        p=run/name
        receipt=json.loads((p/"receipt.json").read_text())
        if sha(p/"conditional-geometry.stl") != receipt["output_sha256"]:
            raise ValueError("Voxel result hash mismatch")
        geometry=trimesh.load(p/"conditional-geometry.stl",process=True)
        scan_receipts[name]={**receipt,"export_watertight":bool(geometry.is_watertight),
                            "export_volume_mm3_conditional":float(geometry.volume),
                            "connected_components":len(geometry.split(only_watertight=False))}
    if not scan_receipts["993-voxel-witness"]["export_watertight"]:
        raise ValueError("Known closed mesh witness did not survive voxelisation")
    witness_error=abs(scan_receipts["993-voxel-witness"]["voxel_volume_mm3_conditional"]/volume-1)
    if witness_error>.01:
        raise ValueError("Closed mesh witness volume error exceeds 1 percent")
    report={"status":"executed_conditional_alloy_screen_993_and_rejected_935_closure",
            "date":"2026-10-03",
            "source_deck_sha256":prep["source_deck_sha256"],
            "material_cards_sha256":sha(cards_path),
            "preparation_sha256":sha(run/"993-cases/preparation.json"),
            "modal_native_sha256":{n:sha(run/"993-cases/alsi10mg"/n) for n in ("modal.inp","modal.dat","log.modal")},
            "runtime":runtime,
            "geometry_993":{"basis":"closed PicoGK visual reference, not measured OEM fan",
            "volume_mm3":volume,"triangles":len(mesh.faces),"rotor_review_sha256":sha(run/"993-reference-review-mm.stl"),
            "rotation_axis":"local Z in parametric model; not a registered vehicle datum",
            "bearing_hub_hardware_mass_included":False,"dimensional_validation":False},
            "fresh_solver_runs":{"static":3,"unprestressed_modal":1},"materials":cases,
            "rpm_sweep":rows,"similarity_checks":similarity_errors,
            "935":{"status":"blocked_volume_reconstruction_before_mass_or_fea",
            "mass_kg":None,"maximum_stress_MPa":None,"system_assembly_registered":False,
            "scan_scale_verified":False,"voxel_experiments":scan_receipts},
            "safe_speed_rpm":None,"fatigue_life_cycles":None,"installed_airflow_m3_s":None,
            "whole_system_structural_validation":False,"mesh_independence_demonstrated":False,
            "digital_twin_calibrated":False,"manufacturing_authorized":False,
            "closed_mesh_witness_relative_volume_error":witness_error}
    if (run/"execution.json").is_file():
        execution=json.loads((run/"execution.json").read_text())
        if len(execution["cases"])!=4 or any(c["returncode"]!=0 for c in execution["cases"]):
            raise ValueError("Incomplete native execution receipt")
        report["native_execution_receipt_sha256"]=sha(run/"execution.json")
        (output/"execution.json").write_bytes((run/"execution.json").read_bytes())
    (output/"comparison.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    with (output/"rpm-sweep.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader();writer.writerows(rows)
    # A separate USD asset per material keeps analysis metadata with the geometry.
    for case in cases:
        target=output/(case["id"]+"-993-study.usda")
        stage=Usd.Stage.CreateNew(str(target));UsdGeom.SetStageMetersPerUnit(stage,1.)
        UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
        root=UsdGeom.Xform.Define(stage,"/FanStudy");stage.SetDefaultPrim(root.GetPrim())
        root.GetPrim().SetCustomData({"status":"uncalibrated_993_parametric_rotor_material_study",
            "material":case["id"],"physicalValidation":False,"manufacturingAuthorized":False,
            "caseResults":"comparison.json","geometrySHA256":sha(run/"993-reference-review-mm.stl"),
            "massKg":case["mass_kg"],"polarInertiaKgM2":case["polar_inertia_kg_m2"],
            "densityKgM3":case["material"]["density_g_cm3"]*1000,
            "youngModulusPa":case["material"]["young_modulus_GPa"]*1e9,
            "poissonRatioAssumed":cards["poisson_ratio_common_assumed"],
            "peakStressMPaAt10000RPM":case["static_10000rpm"]["von_mises_max_MPa"],
            "maximumDisplacementMmAt10000RPM":case["static_10000rpm"]["maximum_displacement_mm"]})
        surface=UsdGeom.Mesh.Define(stage,"/FanStudy/Rotor")
        surface.CreatePointsAttr([Gf.Vec3f(*v) for v in mesh.vertices*.001])
        surface.CreateFaceVertexCountsAttr([3]*len(mesh.faces));surface.CreateFaceVertexIndicesAttr(mesh.faces.flatten().tolist())
        surface.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        stage.GetRootLayer().Save()
        reopened=Usd.Stage.Open(str(target))
        if not reopened or UsdGeom.GetStageMetersPerUnit(reopened)!=1.:
            raise ValueError("USD round trip failed")
    # Exportable plots, with cases outside the linear comparator explicitly marked.
    fig,axes=plt.subplots(2,2,figsize=(12,9),layout="constrained")
    colors=["#2264ac","#19865c","#9a4fbe"]
    labels=["AlSi10Mg","WE43 (carte élastique indicative)","Ti-6Al-4V"]
    axes[0,0].bar(labels,[c["mass_kg"]*1000 for c in cases],color=colors)
    axes[0,0].set(ylabel="Masse rotor seul (g)",title="Même forme PicoGK 993 : volume 283,90 cm³")
    for c,color,label in zip(cases,colors,labels):
        selected=[r for r in rows if r["material"]==c["id"]]
        x=[r["rpm_rotor"] for r in selected]
        axes[0,1].plot(x,[r["peak_von_mises_MPa"] for r in selected],"o-",label=label,color=color)
        axes[1,0].plot(x,[r["maximum_displacement_mm"] for r in selected],"o-",label=label,color=color)
        axes[1,1].plot(range(1,13),c["modes_hz"],"o-",label=label,color=color)
    axes[0,1].axhline(250,color=colors[0],ls="--",label="Comparateur Al T6, pas une admissible")
    axes[0,1].set(xlabel="Régime du rotor (tr/min)",ylabel="Pic von Mises (MPa)",title="Efforts centrifuges : calcul élastique")
    axes[1,0].set(xlabel="Régime du rotor (tr/min)",ylabel="Déplacement maximal (mm)",title="Fixation de l'alésage hypothétique")
    axes[1,1].set(xlabel="Mode",ylabel="Fréquence (Hz)",title="Modes sans précontrainte, sans paliers ni gyroscopie")
    for ax in axes.flat:ax.grid(alpha=.2)
    axes[0,1].legend(fontsize=7);axes[1,1].legend(fontsize=7)
    fig.suptitle("ÉTUDE 993 CONDITIONNELLE — géométrie et procédé non qualifiés",fontsize=13)
    fig.savefig(output/"comparison.png",dpi=180)
    with PdfPages(output/"comparison.pdf") as pdf:pdf.savefig(fig)
    plt.close(fig)
    (output/"manifest.json").write_text(json.dumps({"files_sha256":{p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
        "checks":{"fresh_solver_output_coverage":"86640 elements and 164869 nodes per static case",
        "material_similarity_checks_passed":True,"openusd_roundtrip_passed":True,
        "closed_geometry_required_for_mass":True},"physical_validation":False},indent=2)+"\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path);parser.add_argument("cards",type=Path);parser.add_argument("output",type=Path)
    parser.add_argument("--runtime",default="See per-case solver version and execution record")
    a=parser.parse_args();build(a.run,a.cards,a.output,a.runtime)
    print("Comparison, CSV, PDF chart and three study USD assets written")
