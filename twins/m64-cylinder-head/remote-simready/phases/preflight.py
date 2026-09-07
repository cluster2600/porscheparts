from common import Phase
from pathlib import Path

if __name__ == "__main__":
    p = Phase("preflight", preflight=True)
    # Upstream preflight specifically resolves <venv-root>/simready-validate.
    # Reuse the image's pinned runtime; do not reinstall or alter it.
    runtime = p.root / "runtime"
    runtime.mkdir(mode=0o700)
    target = Path("/opt/m64-simready-validate")
    if not (target / "bin/simready-validate").is_file():
        raise SystemExit("pinned SimReady runtime missing")
    (runtime / "simready-validate").symlink_to(target, target_is_directory=True)
    raise SystemExit(p.invoke("preflight", [
        "--check-only", "--skip-deploy", "--no-update", "--skip-uv-sync",
        "--targets", "conversion,validation,content-agents",
        "--source-asset", p.input("assembly.step"), "--source-format", "step",
        "--conversion-tools", "usd-convert-cad",
        "--output-root", p.output, "--state-root", p.output / "state",
        "--venv-root", runtime,
        "--env-file", p.output / "preflight.env",
        "--markdown-report", p.output / "reference.md",
    ], script="preflight.py"))
