"""Editable CHF planning model. Never an origin certification or supplier quote."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def amount(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError("invalid cost") from error
    if not number.is_finite() or number < 0:
        raise ValueError("invalid cost")
    return number


def costs(path):
    totals, seen = {}, set()
    with Path(path).open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            key = (row["scenario"], row["item"])
            if not all(key) or key in seen:
                raise ValueError("empty or duplicate cost item")
            seen.add(key)
            low, high = amount(row["low_chf"]), amount(row["high_chf"])
            if low > high:
                raise ValueError("reversed cost range")
            current = totals.setdefault(row["scenario"], [Decimal(0), Decimal(0)])
            current[0] += low
            current[1] += high
    if not totals:
        raise ValueError("empty budget")
    return totals


def origin(path, rd_ch="0", rd_foreign="0", units=1000):
    if type(units) is not int or units < 1:
        raise ValueError("units must be a positive integer")
    swiss, total, excluded = Decimal(0), Decimal(0), Decimal(0)
    seen = set()
    with Path(path).open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if not row["item"] or row["item"] in seen:
                raise ValueError("empty or duplicate origin item")
            seen.add(row["item"])
            value = amount(row["cost_chf"])
            if row["origin"] not in {"CH", "FOREIGN", "UNKNOWN"}:
                raise ValueError("unknown origin code")
            if row["treatment"] == "exclude":
                excluded += value
            elif row["treatment"] == "include":
                total += value
                if row["origin"] == "CH":
                    swiss += value
            else:
                raise ValueError("unknown cost treatment")
    if not seen:
        raise ValueError("empty origin ledger")
    swiss += amount(rd_ch) / units
    total += (amount(rd_ch) + amount(rd_foreign)) / units
    if not total:
        raise ValueError("empty admissible denominator")
    return swiss, total, excluded, 100 * swiss / total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=Path, default=ROOT / "budget.csv")
    parser.add_argument("--origin", type=Path, default=ROOT / "swissness.csv")
    parser.add_argument("--rd-ch", default="0")
    parser.add_argument("--rd-foreign", default="0")
    parser.add_argument("--units", type=int, default=1000)
    args = parser.parse_args()
    totals = costs(args.budget)
    for scenario, (low, high) in totals.items():
        print(f"{scenario}: CHF {low:.2f} - {high:.2f}")
    if "nre" in totals:
        for count in (100, 1000):
            low, high = totals["nre"]
            print(f"partial_nre_per_unit_at_{count}: CHF {low/count:.2f} - {high/count:.2f}")
    swiss, total, excluded, percent = origin(args.origin, args.rd_ch, args.rd_foreign, args.units)
    print(f"ILLUSTRATIVE_ONLY: CH {swiss:.2f} / admissible {total:.2f} = {percent:.2f}%")
    print(f"excluded_economic_costs: CHF {excluded:.2f}; essential Swiss activity NOT VERIFIED")


if __name__ == "__main__":
    main()
