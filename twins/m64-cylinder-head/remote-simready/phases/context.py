from common import Phase

if __name__ == "__main__":
    p = Phase("context")
    p.input("asset-context.json")
    raise SystemExit(p.invoke("identify-asset-context", [
        p.input("assembly.step"), "--markdown-report", p.output / "reference.md",
    ]))
