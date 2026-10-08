#!/usr/bin/env python3
"""Write the LPBF print simulation section into each 993 design dossier.

The section sits between two markers and is rewritten on every pass: it follows
the published report, never the reverse. `--check` fails if a dossier differs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- print-screen:begin -->"
END = "<!-- print-screen:end -->"

SHEETS = {
    "993-body-front-impact-support-alsi10mg-f0-0001": "993_FRONT_IMPACT_SUPPORT_ALSI10MG_F0.md",
    "993-eng-connecting-rod-ti64-f0-0001": "993_CONNECTING_ROD_TI64_F0.md",
    "993-eng-cooling-impeller-alsi10mg-f0-0001": "993_COOLING_IMPELLER_ALSI10MG_F0.md",
    "993-eng-cooling-impeller-we43-f1-0001": "993_COOLING_IMPELLER_WE43_F1.md",
    "993-eng-fan-stator-alsi10mg-f1-0001": "993_FAN_STATOR_ALSI10MG_F1.md",
    "993-eng-exhaust-manifold-in625-f0-0001": "993_EXHAUST_MANIFOLD_IN625_F0.md",
    "993-eng-fan-housing-alsi10mg-f0-0001": "993_FAN_HOUSING_ALSI10MG_F0.md",
    "993-eng-intake-valve-ti64-hollow-f0-0001": "993_INTAKE_VALVE_TI64_HOLLOW_F0.md",
    "993-eng-intercooler-bracket-ti-f0-0001": "993_INTERCOOLER_BRACKET_TI_F0.md",
    "993-eng-intercooler-end-tank-alsi10mg-f0-0001": "993_INTERCOOLER_END_TANK_ALSI10MG_F0.md",
    "993-eng-k16-compressor-wheel-al2139-f1-0001": "993_K16_COMPRESSOR_WHEEL_AL2139_F1.md",
    "993-eng-k16-compressor-wheel-alsi10mg-f0-0001": "993_K16_COMPRESSOR_WHEEL_ALSI10MG_F0.md",
    "993-eng-k16-turbine-wheel-in718-f0-0001": "993_K16_TURBINE_WHEEL_IN718_F0.md",
    "993-eng-oil-filter-console-alsi10mg-f0-0001": "993_OIL_FILTER_CONSOLE_ALSI10MG_F0.md",
    "993-eng-three-runner-intake-alsi10mg-f0-0001": "993_THREE_RUNNER_INTAKE_ALSI10MG_F0.md",
    "993-eng-turbo-heat-shield-in625-f0-0001": "993_TURBO_HEAT_SHIELD_IN625_F0.md",
    "993-eng-turbo-oil-return-line-in625-f0-0001": "993_TURBO_OIL_RETURN_LINE_IN625_F0.md",
    "993-eng-upper-valve-cover-alsi10mg-f0-0001": "993_UPPER_VALVE_COVER_ALSI10MG_F0.md",
    "993-whl-center-cap-alsi10mg-f0-0001": "993_WHEEL_CENTER_CAP_ALSI10MG_F0.md",
    "993-elec-headlamp-spring-hook-f0-0001": "993_HEADLAMP_SPRING_HOOK_ALSI10MG_F0.md",
    "993-exh-oval-tip-in625-f0-0001": "993_OVAL_EXHAUST_TIP_IN625_F0.md",
}

REASONS = {
    "no_orientation_fits_bare_machine_envelope": "none of the candidate orientations fits the EOS M 290 envelope (250 x 250 x 325 mm)",
    "surface_mesh_not_single_component": "the STEP master is not a single body; slicing refuses a surface in several pieces",
}


def fr(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}"


def section(slug: str, sheet: Path, status: dict) -> str:
    folder = ROOT / f"parts/{slug}/evidence/lpbf-f0"
    reports = sorted(folder.glob("*-lpbf-geometry-report.json"))
    lines = [BEGIN, "", "## LPBF print simulation", ""]
    if reports:
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        image = reports[0].with_name(reports[0].name.replace("-report.json", "-screen.png"))
        link = os.path.relpath(image, sheet.parent)
        s, t, p = report["full_build_slicing"], report["thickness_screen"], report["powder_escape_screen"]
        lines += [
            f"The STEP was tessellated, then sliced over its full height at `{fr(s['layer_thickness_mm'] * 1000, 0)} µm`, "
            f"on the EOS M 290 route of the candidate material. Orientation chosen by the automatic rule: "
            f"`{report['selected_candidate_orientation']}`.",
            "",
            "| quantity | value |",
            "|---|---:|",
            f"| layers | {s['layer_count']:,} |",
            f"| build height | {fr(s['build_height_mm'])} mm |",
            f"| layers with an unsupported region | {s['layers_with_unsupported_area']} |",
            f"| support proxy | {fr(s['support_proxy_volume_mm3'])} mm³ |",
            f"| local thickness p01 | {fr(t['p01_mm'], 3)} mm |",
            f"| trapped powder at {fr(p['pitch_mm'])} mm | {fr(p['trapped_void_volume_mm3'])} mm³ |",
            "",
            f"![LPBF print simulation]({link})",
            "",
            "This screening is neither an EOSPRINT project, nor a distortion calculation, nor a "
            "recoater check. **Printing remains prohibited.**",
        ]
    else:
        row = status.get(slug, {})
        error = (row.get("error") or "").strip().splitlines()[-1:] or [""]
        code = error[0].replace("METAL AM FAIL-CLOSED: ", "")
        reason = REASONS.get(code, f"`{row.get('status', 'not run')}` {code}".strip())
        lines += [
            f"The simulation was run and **failed closed**: {reason}. "
            "No result is therefore published for this part, and no image is made up in its place.",
        ]
    lines += ["", END]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    status = json.loads(args.status.read_text(encoding="utf-8")) if args.status.exists() else {}
    stale = []
    for slug, name in SHEETS.items():
        sheet = ROOT / "docs/993" / name
        text = sheet.read_text(encoding="utf-8")
        block = section(slug, sheet, status)
        if BEGIN in text:
            head, rest = text.split(BEGIN, 1)
            new = head + block + rest.split(END, 1)[1]
        else:
            new = text.rstrip("\n") + "\n\n" + block + "\n"
        if new != text:
            stale.append(name)
            if not args.check:
                sheet.write_text(new, encoding="utf-8")
    for name in stale:
        print(("STALE " if args.check else "wrote ") + name)
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
