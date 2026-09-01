#!/usr/bin/env python3
"""Build a traceable quantitative ledger from the searchable 993 manual.

The manual itself is not copied into this repository. This script records short
factual rows, page numbers and the extraction status so a reader can check every
value against an authorised copy. It combines the already structured tables
from Porsche Fanatics with a page-by-page OCR index for measurements that occur
inside repair procedures.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "SRC-PORSCHE-WORKSHOP-MANUAL-993"
MANUAL_PAGES = 1481
MANUALLY_CHECKED_PAGES = [15, 19, 98, 108, 121, 137, 152, 153, 154, 155, 156, 157, 177, 258, 725, 726, 727, 728]

NUMBER = r"[+-]?\d+(?:[.,]\d+)?"
VALUE = (
    rf"{NUMBER}(?:\s*(?:x|×|\+|/|:)\s*{NUMBER})*"
    rf"(?:\s*(?:to|[-–—]|±|\.\.\.|…)\s*{NUMBER}"
    rf"(?:\s*(?:x|×|\+|/|:)\s*{NUMBER})*)?"
)

# The order matters: longer units must be tried before their shorter forms.
# Avoid matching dimension labels such as "M 64/05" or "A = ..." as units.
# Dimension and engineering units are matched in their normal spelling;
# ambiguous one-letter units are retained only when their surrounding line
# clearly describes an electrical, power, mass or capacity measurement. The
# bare metre unit is intentionally omitted because it is not useful in this
# manual's OCR without a surrounding context.
UNIT_PATTERN = re.compile(
    rf"(?P<value>{VALUE})\s*(?P<unit>"
    r"cm(?:2|²)?|mm(?:2|²)?|µm|um|km/h|km|mph|inches?|in\.?|ft|kg|lbs?|mg|"
    r"Nm|N[·.]?m|kPa|mbar|bar|psi|kN|N|rpm|r/min|degrees?|liters?|litres?|"
    r"Ohms?|ohm|sec(?:onds?)?|min(?:utes?)?|hours?|"
    r"g|V|mV|A|mA|W|kW|HP|°C|°F|°|mL|L|%"
    r")(?=$|[^A-Za-z])|(?P<percent_value>{NUMBER})\s*%"
)
THREAD_PATTERN = re.compile(
    rf"\bM\s*{NUMBER}(?:\s*x\s*{NUMBER})?(?:\s*x\s*{NUMBER})?\b",
    re.IGNORECASE,
)


def clean(text: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    return value[:limit]


def measurement_context(line: str, start: int, end: int) -> str:
    """Keep a short locator around a value, not a copied procedure sentence."""
    left = max(0, start - 48)
    right = min(len(line), end + 48)
    return clean(line[left:right], 120)


def kind_for(line: str, unit: str) -> str:
    text = line.lower()
    if "wear limit" in text or ("wear" in text and "limit" in text):
        return "wear_limit"
    if any(word in text for word in ("clearance", "backlash", "play", "runout", "tolerance", "deviation", "press fit", "interference")):
        return "tolerance_or_clearance"
    if unit.lower() in {"nm", "n·m", "n.m"}:
        return "torque"
    if unit.lower() in {"bar", "mbar", "kpa", "psi"}:
        return "pressure"
    if unit.lower() in {"n", "kn"}:
        return "force_or_load"
    if unit.lower() in {"ohm", "ohms"}:
        return "electrical_resistance"
    if unit.lower() in {"kg", "g", "mg", "lbs", "lb"}:
        return "mass"
    if unit.lower() in {"rpm", "r/min", "km/h", "mph"}:
        return "speed"
    if unit.lower() in {"sec", "secs", "second", "seconds", "min", "mins", "minute", "minutes", "hour", "hours"}:
        return "duration"
    if unit == "%":
        return "percentage"
    if unit.lower() in {"degrees", "degree", "°", "°c", "°f"}:
        return "angle_or_temperature"
    if unit.lower() in {"l", "ml", "milliliter", "milliliters", "liter", "liters", "litre", "litres"}:
        return "capacity"
    if unit.lower() in {"v", "mv", "a", "ma", "w", "kw", "hp"}:
        return "electrical_or_power"
    return "dimension"


def keep_unit_occurrence(line: str, unit: str) -> bool:
    """Reject common OCR false positives for ambiguous one-letter units."""
    lower = line.lower()
    if unit in {"A", "mA"}:
        return bool(re.search(r"alternator|current|amp(?:ere)?|output|electrical|voltage", lower))
    if unit in {"V", "mV"}:
        return bool(re.search(r"voltage|display|sensor|supply|battery|electrical|signal", lower))
    if unit in {"W", "kW", "HP"}:
        return bool(re.search(r"power|output|engine|sae|eec|watt|hp", lower))
    if unit == "g":
        return bool(re.search(r"weight|mass|gram|weigh|connecting rod|piston", lower))
    if unit in {"L", "mL"}:
        return bool(re.search(r"capacity|volume|fluid|oil|fuel|liter|litre|reservoir", lower))
    if unit in {"N", "kN"}:
        return bool(re.search(r"force|load|spring|pressure|tension|strength|newton", lower))
    if unit.lower() in {"ohm", "ohms"}:
        return bool(re.search(r"resistance|ohm|electrical|sensor|coil|relay|motor", lower))
    return True


def page_header(page_text: str) -> str:
    lines = [clean(line, 100) for line in page_text.splitlines() if line.strip()]
    for line in lines[:20]:
        if re.search(r"911\s+Carrera|Technical data|Repair Manual", line, re.IGNORECASE):
            return line
    return lines[0] if lines else ""


def variant_for(page_text: str) -> str | None:
    if re.search(r"Carrera\s+4S|Turbo[- ]Look", page_text, re.IGNORECASE):
        return "Carrera_4S_Turbo_Look"
    if re.search(r"Carrera\s*\(993\)", page_text, re.IGNORECASE) and re.search(r"Carrera\s+RS", page_text, re.IGNORECASE):
        return "Carrera_and_RS"
    if re.search(r"Carrera\s+4", page_text, re.IGNORECASE):
        return "Carrera_4"
    if re.search(r"Carrera\s+RS", page_text, re.IGNORECASE):
        return "Carrera_RS"
    if re.search(r"Carrera\s*\(993\)", page_text, re.IGNORECASE):
        return "Carrera"
    return None


def raw_measurements(raw_path: Path) -> list[dict[str, Any]]:
    pages = raw_path.read_text(encoding="utf-8", errors="replace").split("\f")
    entries: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int, str, str]] = set()

    for page, page_text in enumerate(pages[:MANUAL_PAGES], start=1):
        header = page_header(page_text)
        variant = variant_for(page_text)
        for line_number, line in enumerate(page_text.splitlines(), start=1):
            for match in UNIT_PATTERN.finditer(line):
                value_text = clean(match.group("value") or match.group("percent_value"), 80)
                unit = match.group("unit") or "%"
                if not keep_unit_occurrence(line, unit):
                    continue
                # In the technical-data table the unit heading follows the
                # standard number in "SAE J 1349 Nm"; 1349 is not a torque.
                if unit == "Nm" and re.search(r"SAE\s+J\s*$", line[: match.start()], re.IGNORECASE):
                    continue
                key = (page, line_number, match.start(), value_text, unit.lower())
                if key in seen:
                    continue
                seen.add(key)
                row: dict[str, Any] = {
                    "pdf_page": page,
                    "line": line_number,
                    "record_type": "ocr_measurement_occurrence",
                    "kind": kind_for(line, unit),
                    "value_text": value_text,
                    "unit": unit,
                    "context": measurement_context(line, match.start(), match.end()),
                    "page_header": header,
                    "extraction_status": "ocr_unreviewed",
                }
                if variant:
                    row["variant_context"] = variant
                entries.append(row)

            # Thread sizes are dimensions even when the source line has no unit.
            for match in THREAD_PATTERN.finditer(line):
                value_text = clean(match.group(0), 80)
                # Bare M64/M64/05 engine designations are not thread sizes. A
                # bare M8 is retained only where the surrounding line names a
                # fastener or a torque-table location; sizes with a pitch or
                # length (M8 x 30) are unambiguous.
                if "x" not in value_text.lower() and not re.search(
                    r"bolt|nut|screw|plug|stud|thread|switch|plate|housing|torque|clamp|guide|selector|vent",
                    line,
                    re.IGNORECASE,
                ):
                    continue
                key = (page, line_number, match.start(), value_text, "thread_spec")
                if key in seen:
                    continue
                seen.add(key)
                row = {
                    "pdf_page": page,
                    "line": line_number,
                    "record_type": "ocr_thread_size_occurrence",
                    "kind": "thread_size",
                    "value_text": value_text,
                    "unit": "thread_spec",
                    "context": measurement_context(line, match.start(), match.end()),
                    "page_header": header,
                    "extraction_status": "ocr_unreviewed",
                }
                if variant:
                    row["variant_context"] = variant
                entries.append(row)
    return entries


def structured_data(path: Path, record_type: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("entries", [])
    output: list[dict[str, Any]] = []
    for row in rows:
        if record_type == "technical_data":
            output.append(
                {
                    "record_type": record_type,
                    "pdf_page": row.get("page"),
                    "label": row.get("label"),
                    "value_text": row.get("value"),
                    "unit": row.get("unit", ""),
                    "subject": row.get("subject", ""),
                    "extraction_status": "structured_derived",
                }
            )
        else:
            value_text = None
            unit = None
            if row.get("torqueNm") is not None:
                value_text = str(row["torqueNm"])
                unit = "Nm"
            elif row.get("angleDegrees") is not None:
                value_text = str(row["angleDegrees"])
                unit = "degrees"
            elif row.get("note"):
                value_text = row["note"]
                unit = "instruction"
            if value_text is None:
                continue
            output.append(
                {
                    "record_type": record_type,
                    "pdf_page": row.get("page"),
                    "label": row.get("location"),
                    "value_text": value_text,
                    "unit": unit,
                    "thread": row.get("thread", ""),
                    "stage": row.get("stage", ""),
                    "section": row.get("section", ""),
                    "group": row.get("group", ""),
                    "model": row.get("model", ""),
                    "extraction_status": "structured_derived",
                }
            )
    return output


def build(args: argparse.Namespace) -> dict[str, Any]:
    technical = structured_data(args.technical_data, "technical_data")
    torques = structured_data(args.torque_specs, "torque_spec")
    occurrences = raw_measurements(args.raw)
    return {
        "$comment": "Registre des valeurs quantitatives du manuel d'atelier 993. Les tableaux structurés sont des faits dérivés; les occurrences issues de l'OCR doivent être contrôlées visuellement dans l'exemplaire autorisé avant usage de fabrication.",
        "schema_version": "1.0.0",
        "source_id": SOURCE_ID,
        "source": "993 Repair Manual (Porsche AG, 2001 printing), OCR pass 2026-08-28",
        "manual_pdf_pages": MANUAL_PAGES,
        "generated_on": "2026-08-30",
        "extraction": {
            "method": "structured_manual_tables_plus_pdftotext_layout_unit_index",
            "status": "complete_numeric_unit_index",
            "raw_input": "OCR layout text generated from the searchable manual; raw source is not stored in this repository",
            "ocr_status": "occurrences are not individually page-checked",
            "manually_checked_pages": MANUALLY_CHECKED_PAGES,
        },
        "counts": {
            "technical_data": len(technical),
            "torque_specs": len(torques),
            "measurement_occurrences": len(occurrences),
            "total_records": len(technical) + len(torques) + len(occurrences),
        },
        "technical_data": technical,
        "torque_specs": torques,
        "measurement_occurrences": occurrences,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True, help="OCR layout text made from the manual PDF")
    parser.add_argument("--technical-data", type=Path, required=True, help="Porsche Fanatics technical-data.json")
    parser.add_argument("--torque-specs", type=Path, required=True, help="Porsche Fanatics torque-specs.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for path in (args.raw, args.technical_data, args.torque_specs):
        if not path.exists():
            parser.error(f"missing input: {path}")
    payload = build(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = payload["counts"]
    print(
        f"wrote {args.output}: {counts['technical_data']} technical, "
        f"{counts['torque_specs']} torque, {counts['measurement_occurrences']} OCR occurrences"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
