"""Summarize local build receipts without copying logs or host-specific paths."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("receipts", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
results = []
for recipe in sorted(root.glob("*.Dockerfile")):
    digest = hashlib.sha256(recipe.read_bytes()).hexdigest()
    attempts = []
    for directory in args.receipts.glob(recipe.stem + ".*"):
        if not (directory / "build-exit-code.txt").exists():
            continue
        item = {"receipt": directory.name}
        for key, name in (("build_exit", "build-exit-code.txt"),
                          ("smoke_exit", "smoke-exit-code.txt")):
            path = directory / name
            item[key] = int(path.read_text()) if path.exists() else None
        for key, name in (("image", "image.txt"), ("recipe_sha256", "recipe.sha256"),
                          ("started", "started.txt"), ("finished", "finished.txt")):
            path = directory / name
            if path.exists():
                item[key] = path.read_text().strip()
        attempts.append(item)
    attempts.sort(key=lambda item: (item.get("started", ""), item["receipt"]))
    matching = [item for item in attempts
                if item.get("recipe_sha256", "").split()[0:1] == [digest]]
    latest = matching[-1] if matching else None
    passed = bool(latest and latest["build_exit"] == 0 and latest["smoke_exit"] == 0)
    results.append({"name": recipe.stem,
                    "recipe": "containers/stack-20261105/" + recipe.name,
                    "current_recipe_sha256": digest,
                    "attempts": attempts, "passed": passed,
                    "current_receipt": latest["receipt"] if latest else None})
(root / "build-results.json").write_text(json.dumps({
    "scope": "Linux amd64 CPU checks only; no GPU acceptance",
    "images": results}, indent=2) + "\n")
inventory_path = root / "inventory.json"
inventory = json.loads(inventory_path.read_text())
by_name = {item["name"]: item for item in results}
for row in inventory["recipes"]:
    original = Path(row["original_recipe"])
    name = original.parent.name if original.name == "Dockerfile" else original.stem
    candidate = row.get("candidate_recipe")
    result = by_name.get(Path(candidate).stem if candidate else name)
    if result:
        row["candidate_recipe"] = result["recipe"]
        row["status"] = "built_cpu_smoke_passed" if result["passed"] else "prepared_not_passed"
        row["build_receipt"] = result["current_receipt"]
inventory_path.write_text(json.dumps(inventory, indent=2) + "\n")
print(json.dumps({"passing_current_recipes": sum(item["passed"] for item in results),
                  "prepared": len(results), "inventory": inventory["recipe_count"]}))
