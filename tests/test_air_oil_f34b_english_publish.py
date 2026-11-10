"""Static guard for the English F34b publication workflow (issue #607).

The English workflow must publish the English generation's context with
exactly the historical F34b gates: same pinned actions, same digest,
attestation, SBOM, hardened-smoke and anonymous-pull checks. Only the image
name, the build context, the static tests and the evidence file names may
differ. The historical workflow, Dockerfile and lock are not touched.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGLISH = ROOT / ".github" / "workflows" / "air-oil-cycle-f34b-english-image.yml"
HISTORICAL = ROOT / ".github" / "workflows" / "air-oil-cycle-f34b-image.yml"
GENERATION = "containers/air-oil-cycle-f34b-en-20261106"


def step(workflow: str, name: str) -> str:
    start = workflow.index(f"      - name: {name}\n")
    following = workflow.find("\n      - name: ", start + 1)
    return workflow[start:] if following == -1 else workflow[start:following]


def normalised(text: str) -> str:
    return text.replace("air-oil-cycle-f34b-en-", "air-oil-cycle-f34b-")


class EnglishPublicationWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.english = ENGLISH.read_text(encoding="utf-8")
        cls.historical = HISTORICAL.read_text(encoding="utf-8")

    def test_manual_main_only_with_package_write(self):
        triggers = self.english[self.english.index("\non:\n"):self.english.index("\npermissions:")]
        self.assertEqual(triggers.strip(), "on:\n  workflow_dispatch:")
        for fragment in (
            "  contents: read\n",
            "  packages: write\n",
            'test "${GITHUB_REF}" = "refs/heads/main"',
            'test "${GITHUB_SHA}" = "$(git rev-parse HEAD)"',
            "group: air-oil-cycle-f34b-en-${{ github.sha }}",
            "cancel-in-progress: false",
        ):
            self.assertIn(fragment, self.english)

    def test_builds_the_english_context_under_its_own_name(self):
        self.assertIn(
            "IMAGE_REPOSITORY: ghcr.io/${{ github.repository_owner }}/3dprinting993-air-oil-cycle-f34b-en\n",
            self.english,
        )
        self.assertIn(f'python3 {GENERATION}/prepare_context.py "${{RUNNER_TEMP}}/f34b-en"', self.english)
        self.assertIn("context: ${{ runner.temp }}/f34b-en\n", self.english)
        self.assertIn(f"file: ${{{{ github.workspace }}}}/{GENERATION}/Dockerfile\n", self.english)
        self.assertNotIn("containers/air-oil-cycle-f34b.Dockerfile", self.english)
        self.assertIn("scope=air-oil-cycle-f34b-en\n", self.english)
        for test in ("test_air_oil_f34b_english_generation.py", "test_air_oil_f34b_native_receipt.py",
                     "test_air_oil_f34b_english_publish.py"):
            self.assertIn(f"python3 tests/{test} -v", self.english)

    def test_pinned_actions_match_the_historical_workflow(self):
        uses = re.compile(r"uses: (\S+)")
        self.assertEqual(sorted(set(uses.findall(self.english))), sorted(set(uses.findall(self.historical))))
        for action in uses.findall(self.english):
            self.assertRegex(action, r"@[0-9a-f]{40}$")

    def test_gates_are_the_historical_gates(self):
        for name in (
            "Verify main release source",
            "Set up pinned Buildx",
            "Verify pinned Buildx and BuildKit",
            "Log in to GHCR for publication",
            "Gate exact digest, attestations, SBOM and hardened smoke",
            "Log in to GHCR for verified tag promotion",
            "Promote verified digest to unique verified tag",
        ):
            self.assertEqual(normalised(step(self.english, name)), step(self.historical, name), name)

    def test_build_step_differs_only_in_context_file_and_cache(self):
        name = "Build and publish linux/amd64 candidate with attestations"
        english = step(self.english, name).splitlines()
        historical = step(self.historical, name).splitlines()
        self.assertEqual(len(english), len(historical))
        changed = {(a.strip().split(":")[0]) for a, b in zip(english, historical) if a != b}
        self.assertEqual(changed, {"context", "file", "cache-from", "cache-to"})

    def test_in_image_paths_are_unchanged(self):
        self.assertIn("/opt/air-oil-cycle-f34b/scripts/run_917_air_oil_cycle_f34b.py", self.english)
        self.assertNotIn("/opt/air-oil-cycle-f34b-en", self.english)

    def test_evidence_is_retained_under_english_names(self):
        upload = step(self.english, "Upload immutable image evidence")
        self.assertIn("name: air-oil-cycle-f34b-en-${{ github.sha }}-${{ github.run_id }}-${{ github.run_attempt }}", upload)
        for name in ("image-ref.txt", "anonymous-audit.json", "anonymous-pull.txt", "sbom.json", "provenance.json",
                     "source-inputs.sha256", "context.sha256"):
            self.assertIn(f"air-oil-cycle-f34b-en-{name}", upload)
        self.assertIn("if: always()", upload)


if __name__ == "__main__":
    unittest.main()
