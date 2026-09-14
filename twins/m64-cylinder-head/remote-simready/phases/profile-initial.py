from common import Phase

if __name__ == "__main__":
    p = Phase("profile-initial")
    raise SystemExit(p.invoke("simready-validate", [
        p.asset_from("physics"), "--profile", "Prop-Robotics-Neutral", "--profile-version", "1.0.0",
    ]))
