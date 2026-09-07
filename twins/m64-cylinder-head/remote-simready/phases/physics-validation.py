from common import Phase

if __name__ == "__main__":
    p = Phase("physics-validation")
    p.require("geometry-validation", passed=False)
    raise SystemExit(p.invoke("omni-asset-validate-physics", [p.asset_from("conform"), "--timeout", p.seconds()]))
