from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "twins/reference-917-engine/source/run_rotating_assembly_usd_f35.sh"


class RotatingAssemblyUsdF35RunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RUNNER.read_text(encoding="utf-8")

    def test_runner_uses_one_exact_immutable_cpu_compatible_image(self):
        self.assertIn(
            "ghcr.io/cluster2600/3dprinting993-simready-workflow", self.source
        )
        self.assertIn(
            "sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe",
            self.source,
        )
        self.assertIn("{{json .RepoDigests}}", self.source)
        self.assertIn("linux/amd64", self.source)
        self.assertNotIn(":latest", self.source)

    def test_runner_converts_all_twelve_prototypes_then_authors_both_stages(self):
        for variant in ("type_912_4_5_na", "917_30_turbo_5374"):
            self.assertIn(variant, self.source)
        for family in (
            "crankshaft",
            "main_bearing_pair",
            "connecting_rod",
            "piston",
            "piston_pin",
            "piston_ring",
        ):
            self.assertIn(family, self.source)
        self.assertIn("simready-preflight/convert.py", self.source)
        self.assertIn("author_rotating_assembly_usd_f35.py", self.source)
        self.assertIn("--up-axis z", self.source)
        self.assertIn("conversion-report.json", self.source)

    def test_runner_is_offline_hardened_and_has_no_secret_or_remote_transport(self):
        for token in (
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g",
        ):
            self.assertIn(token, self.source)
        lowered = self.source.lower()
        for forbidden in (
            "docker pull",
            "curl ",
            "wget ",
            "ssh ",
            "openbao",
            "bao kv",
            "security find-",
        ):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
