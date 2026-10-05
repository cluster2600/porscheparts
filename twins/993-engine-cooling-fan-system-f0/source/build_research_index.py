#!/usr/bin/env python3
"""Index four original research lanes without changing their records or admission levels."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

RESEARCH = Path(__file__).resolve().parents[1] / "program/research"


def normalized_url(url):
    if not url:
        return None
    u = urlsplit(url)
    fragment = "" if u.path.lower().endswith(".pdf") and u.fragment.startswith("page=") else u.fragment
    return urlunsplit((u.scheme.lower(), u.netloc.lower(), u.path or "/", u.query, fragment))


def build():
    corpus = RESEARCH / "corpus"
    manifest = json.loads((corpus / "import-manifest.json").read_text())
    for name, sha in manifest["files_sha256"].items():
        if hashlib.sha256((corpus / name).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Original research text changed: {name}")
    specs = {
        "aftermarket": ("aftermarket_catalog.json", "sources", "id"),
        "geometry": ("evidence.json", "source_records", "id"),
        "oem": ("oem_research.json", "sources", "id"),
        "forums": ("forum_corpus.json", "sources", "source_id"),
    }
    groups = {}
    source_sets = {}
    datasets = {}
    for lane, (filename, field, id_field) in specs.items():
        relative = f"{lane}/{filename}"
        dataset = json.loads((corpus / relative).read_text())
        datasets[lane] = dataset
        records = dataset[field]
        ids = [s[id_field] for s in records]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate original source ID in {lane}")
        source_sets[lane] = set(ids)
        for number, record in enumerate(records):
            url = record.get("url")
            identity = normalized_url(url) or f"unresolved:{lane}:{record[id_field]}"
            key = "source-" + hashlib.sha256(identity.encode()).hexdigest()[:16]
            group = groups.setdefault(key, {"canonical_key": key, "normalized_url": normalized_url(url),
                                           "independent_of_project": True, "aliases": []})
            if url:
                parsed = urlsplit(url)
                host = parsed.netloc.lower().removeprefix("www.")
                if host == "porschefanatics.com" or host.endswith(".porschefanatics.com") or (
                    host == "github.com" and parsed.path.startswith("/cluster2600/porscheparts")
                ):
                    group["independent_of_project"] = False
            group["aliases"].append({"lane": lane, "original_source_id": record[id_field],
                                     "file": "corpus/" + relative, "json_pointer": f"/{field}/{number}",
                                     "source_record": record})
    indexed = []

    def add(lane, record_id, relative, pointer, refs, record):
        if any(ref not in source_sets[lane] for ref in refs):
            raise ValueError(f"Unknown original source reference: {lane}:{record_id}")
        indexed.append({"lane": lane, "record_id": record_id, "file": "corpus/" + relative,
                        "locator": pointer, "original_source_ids": refs,
                        "original_record": record, "engineering_validation": False})

    for number, record in enumerate(datasets["aftermarket"]["products"]):
        add("aftermarket", record["id"], "aftermarket/aftermarket_catalog.json", f"/products/{number}",
            record["source_ids"], record)
        if record["validated_for_project"]:
            raise ValueError("Supplier catalogue is not project validation")
    with (corpus / "aftermarket/aftermarket_parameters.csv").open(newline="") as f:
        parameters = list(csv.DictReader(f))
    for number, record in enumerate(parameters):
        add("aftermarket", f"AF-P{number+1:03}", "aftermarket/aftermarket_parameters.csv",
            f"CSV record {number+1} after header", [record["source_id"]], record)
    for number, record in enumerate(datasets["geometry"]["claims"]):
        add("geometry", record["id"], "geometry/evidence.json", f"/claims/{number}",
            record["source_ids"], record)
    for number, record in enumerate(datasets["oem"]["records"]):
        add("oem", f"OEM-R{number+1:03}", "oem/oem_research.json", f"/records/{number}",
            [record["source_id"]], record)
    for number, record in enumerate(datasets["forums"]["claims"]):
        add("forums", record["claim_id"], "forums/forum_corpus.json", f"/claims/{number}",
            [record["source_id"]], record)
        if record["production_dimension"]:
            raise ValueError("Forum record must not become a production dimension")
    contract = json.loads((corpus / "geometry/parameter-contract.json").read_text())
    dictionary = contract["parameter_dictionary"]
    if len({p["id"] for p in dictionary}) != len(dictionary) or any(not p["unit"] for p in dictionary):
        raise ValueError("Parameter dictionary requires unique IDs and explicit units")
    if any(g["current_state"] != "open" for g in contract["acceptance_gates"]):
        raise ValueError("Research contract cannot close engineering gates")
    return {
        "status": "research_index_not_engineering_validation", "transfer_sha256": manifest["transfer_sha256"],
        "deduplication": "exact normalized URLs; PDF page fragments grouped; original access/edition/locator records retained",
        "repetition_is_not_independent_confirmation": True,
        "same_publisher_does_not_mean_same_product_or_variant": True,
        "source_records": sum(len(ids) for ids in source_sets.values()), "distinct_url_groups": len(groups),
        "sources": sorted(groups.values(), key=lambda g: g["canonical_key"]),
        "records": indexed,
        "counts": {"aftermarket_products": len(datasets["aftermarket"]["products"]),
                   "aftermarket_quantitative_claims": len(parameters), "oem_records": len(datasets["oem"]["records"]),
                   "geometry_claims": len(datasets["geometry"]["claims"]), "forum_claims": len(datasets["forums"]["claims"]),
                   "parameter_dictionary": len(dictionary),
                   "computed_quantities": len(contract["computed_quantities"]),
                   "acceptance_gates": len(contract["acceptance_gates"])},
        "parameter_contract": "corpus/geometry/parameter-contract.json",
        "synthetic_index_ids": "AF-P### and OEM-R### identify original row positions lacking IDs; original IDs and text preserved",
        "engineering_validation": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare the checked-in index without writing")
    args = parser.parse_args()
    result = build()
    path = RESEARCH / "source-index.json"
    if args.check:
        if json.loads(path.read_text()) != result:
            raise ValueError("Research index is stale")
        print(f"Research corpus and index passed: {result['source_records']} source records, "
              f"{result['distinct_url_groups']} URL groups; original text hashes preserved")
    else:
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print("Research index written; original lane files unchanged")
