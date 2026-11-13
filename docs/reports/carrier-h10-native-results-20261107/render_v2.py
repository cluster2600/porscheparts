# Render published scalar inputs; this does not rerun scientific admission.
from pathlib import Path
import hashlib,json,math
R=Path(__file__).resolve().parent
CASES=("gravity","combined")
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    inputs_path=R/"figure-inputs.json"
    assert sha(inputs_path)=="928630b5d816a24429d3858da8ba5f1ea10741d858b6bb8bd3e532f7abcdda5d"
    inputs=json.loads(inputs_path.read_text())
    assert inputs["status"]=="portable_actual_H10_plot_scalars"
    data=inputs["data"]
    images = [R / "carrier-h10-full-field-comparison.png", R / "carrier-h10-stress-trend.png"]
    receipt_path = R / "figure.json"
    assert not any(p.exists() for p in images + [receipt_path]), "Preserve existing rendered evidence"
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ceiling = max(1.0, *(100 * d["normalized_energy_difference"] for row in data.values() for d in row)) * 1.3
    criterion = all(d["normalized_energy_difference"] < .01 for row in data.values() for d in row)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), layout="constrained", facecolor="#f3f6fa")
    for ax, case, title in zip(axes, CASES, ("Gravity-labelled study load", "Combined force and torque")):
        values = [100 * d["normalized_energy_difference"] for d in data[case]]
        bars = ax.bar(["H8 → H9\n7-digit exports", "H9 → H10\n17-digit exports"], values, color=["#8299ad", "#117f91"], width=.54)
        ax.axhline(1, color="#b15d2d", linestyle="--", linewidth=1.5, label="1% increment threshold")
        ax.set(title=title, ylabel="Complete energy-norm increment [%]", ylim=(0, ceiling))
        ax.grid(axis="y", alpha=.16); ax.set_axisbelow(True); ax.spines[["top", "right"]].set_visible(False)
        ax.bar_label(bars, labels=[f"{x:.3f}%" for x in values], padding=6, fontsize=13, weight="bold", color="#17334b")
        ax.legend(frameon=False, fontsize=9)
    fig.suptitle("993 Turbo carrier | H10 complete-field comparison", fontsize=17, weight="bold", color="#17334b")
    verdict = "Two-increment numerical criterion met" if criterion else "Two-increment numerical criterion not met"
    fig.supxlabel("Required: two successive complete increments below 1% for each load case.\nHistorical and current comparisons use different output precision; shared H9 scalar differences are retained.\n" + verdict + " · 20,083,501 H10 tetrahedra · identical external geometry", fontsize=9, color="#34495e")
    fig.savefig(images[0], dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), layout="constrained", facecolor="#f3f6fa")
    for ax, case, title in zip(axes, CASES, ("Gravity-labelled study load", "Combined force and torque")):
        metrics = data[case][1]["metrics"]
        for metric, style, color, label in (("VM_volume_weighted_p95_MPa", "o-", "#117f91", "Volume-weighted 95th percentile"),
                                            ("VM_peak_MPa", "x--", "#b15d2d", "Pointwise peak — unresolved")):
            values = [metrics[metric][frame] for frame in ("source", "refined")]
            ax.plot([0, 1], values, style, color=color, label=label)
            for x, value in enumerate(values):
                ax.annotate(f"{value:,.2f}", (x, value), xytext=(0, 10), textcoords="offset points", ha="center", fontsize=9)
        ax.set(yscale="log", xticks=[0, 1], xticklabels=["H9 (17 digits)", "H10 (17 digits)"], ylabel="Von Mises stress [MPa], log scale", title=title)
        ax.grid(alpha=.15); ax.spines[["top", "right"]].set_visible(False); ax.margins(x=.28, y=.35)
        ax.legend(loc="center", fontsize=8, frameon=False)
    fig.suptitle("Complete stress statistics | pointwise peaks remain unresolved", fontsize=16, weight="bold", color="#17334b")
    fig.supxlabel("Actual full-mesh values; no stress clipping or peak removal.\nThe peak is not accepted as a converged stress or a strength qualification.", fontsize=9, color="#34495e")
    fig.savefig(images[1], dpi=150); plt.close(fig)
    result=dict(status="published_actual_scalars_rendered_no_scientific_replay",inputs_sha256=sha(inputs_path),script_sha256=sha(Path(__file__)),images={p.name:sha(p) for p in images},two_successive_increment_criterion_met=criterion)
    receipt_path.write_text(json.dumps(result,indent=2)+chr(10))
    return 0
if __name__=="__main__":raise SystemExit(main())
