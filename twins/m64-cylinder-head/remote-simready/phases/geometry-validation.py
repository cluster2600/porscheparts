from common import Phase

if __name__ == "__main__":
    p = Phase("geometry-validation")
    p.require("asset-validation", passed=False)
    raise SystemExit(p.invoke("omni-asset-validate-geometry", [p.asset_from("conform"), "--timeout", p.seconds()]))
