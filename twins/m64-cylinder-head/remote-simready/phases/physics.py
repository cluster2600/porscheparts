from common import Phase

if __name__ == "__main__":
    p = Phase("physics")
    raise SystemExit(p.invoke("content-agents/references/physics-agent-client", [
        p.asset_from("material"), p.output / "assignment", "--render-backend", "remote",
        "--convert-output-to-usd", "--prompt", p.prompt("physics-prompt.txt"),
        "--timeout", p.seconds(),
    ]))
