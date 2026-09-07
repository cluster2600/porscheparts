from common import Phase

if __name__ == "__main__":
    p = Phase("conform")
    p.require("profile-initial", passed=False)
    raise SystemExit(p.invoke("simready-conform-profile", [
        p.asset_from("physics"), "--output-dir", p.output / "conformed",
        "--profile", "Prop-Robotics-Neutral", "--profile-version", "1.0.0",
        "--source-asset", p.input("assembly.step"),
        "--validation-report", p.root / "results/profile-initial/reference.json",
        "--pipeline-step", "usd-convert-cad", "--pipeline-step", "material-agent-client",
        "--pipeline-step", "physics-agent-client",
    ]))
