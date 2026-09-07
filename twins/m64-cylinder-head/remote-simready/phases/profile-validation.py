from common import Phase

if __name__ == "__main__":
    p = Phase("profile-validation")
    p.require("physics-validation", passed=False)
    raise SystemExit(p.invoke("simready-validate", [
        p.asset_from("conform"), "--profile", "Prop-Robotics-Neutral", "--profile-version", "1.0.0",
    ]))
