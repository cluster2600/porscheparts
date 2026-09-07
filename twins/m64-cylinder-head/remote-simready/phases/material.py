from common import Phase

if __name__ == "__main__":
    p = Phase("material")
    p.require("minimum")
    raise SystemExit(p.invoke("content-agents/references/material-agent-client", [
        p.asset_from("convert"), p.output / "assignment",
        "--prompt", p.prompt("material-prompt.txt"), "--timeout", p.seconds(),
    ]))
