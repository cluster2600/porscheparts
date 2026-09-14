from common import Phase

if __name__ == "__main__":
    p = Phase("convert")
    p.require("context")
    raise SystemExit(p.invoke("convert-to-usd", [p.input("assembly.step"), p.output / "converted"]))
