from common import Phase

if __name__ == "__main__":
    p = Phase("minimum")
    raise SystemExit(p.invoke("validate-usd-minimum", [p.asset_from("convert")]))
