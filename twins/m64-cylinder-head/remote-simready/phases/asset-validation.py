from common import Phase

if __name__ == "__main__":
    p = Phase("asset-validation")
    raise SystemExit(p.invoke("omni-asset-validate", [p.asset_from("conform"), "--timeout", p.seconds()]))
