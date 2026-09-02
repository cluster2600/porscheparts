"""Garde-fous de l'image CPU OpenFOAM/AATE F35."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OpenFoamEngineF35ImageTests(unittest.TestCase):
    def test_recipe_is_amd64_pinned_and_narrow(self):
        dockerfile = (ROOT / "containers/openfoam-engine-f35.Dockerfile").read_text(
            encoding="utf-8"
        )
        self.assertIn("ubuntu:24.04@sha256:33ceb719", dockerfile)
        self.assertIn('test "${TARGETARCH}" = "amd64"', dockerfile)
        self.assertIn("OPENFOAM_PACKAGE_VERSION=20260724", dockerfile)
        self.assertIn('"openfoam14=${OPENFOAM_PACKAGE_VERSION}"', dockerfile)
        self.assertIn("python3=3.12.3-0ubuntu2.1", dockerfile)
        self.assertIn("AATE_COMMIT=c0f75f953d67cd325d28d1300672d14288f22934", dockerfile)
        self.assertIn("AATE_ARCHIVE_SHA256=28ee8d96b6943fab11b3d70ea3befe472d06d24741962cdb399b1d54e7ff7d3b", dockerfile)
        self.assertNotIn("gmsh", dockerfile.lower())
        self.assertNotIn("calculix", dockerfile.lower())
        self.assertNotIn("openssh", dockerfile.lower())
        self.assertNotIn("blender", dockerfile.lower())
        self.assertIn('org.opencontainers.image.licenses="GPL-3.0-or-later"', dockerfile)

    def test_runtime_is_non_root_and_build_runs_real_solver_smokes(self):
        dockerfile = (ROOT / "containers/openfoam-engine-f35.Dockerfile").read_text(
            encoding="utf-8"
        )
        smoke = (ROOT / "containers/openfoam-engine-f35-smoke.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("USER ${OPENFOAM_ENGINE_UID}:${OPENFOAM_ENGINE_GID}", dockerfile)
        self.assertIn("RUN --network=none openfoam-engine-f35-smoke", dockerfile)
        self.assertIn("foamRun -solver incompressibleFluid", smoke)
        self.assertIn("mpirun --oversubscribe --np 2", smoke)
        self.assertIn("decomposePar -case", smoke)
        self.assertIn('"engine_simulation_proved":false', smoke)
        self.assertIn('"performance_1600_hp_proved":false', smoke)

    def test_build_context_is_allow_listed(self):
        ignore = (
            ROOT / "containers/openfoam-engine-f35.Dockerfile.dockerignore"
        ).read_text(encoding="utf-8")
        self.assertTrue(ignore.startswith("*\n"))
        self.assertIn("!containers/openfoam-engine-f35-smoke.sh", ignore)
        self.assertIn("!benchmarks/openfoam-poiseuille-f25/**", ignore)
        self.assertNotIn("raw", ignore.lower())

    def test_publication_workflow_is_manual_digest_gated_and_anonymous(self):
        workflow = (
            ROOT / ".github/workflows/openfoam-engine-f35-image.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("confirm_openfoam_source_compliance:", workflow)
        self.assertIn('test "${{ inputs.confirm_openfoam_source_compliance }}" = "true"', workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn('test "${GITHUB_REF}" = "refs/heads/main"', workflow)
        self.assertIn("platforms: linux/amd64", workflow)
        self.assertIn("provenance: mode=max", workflow)
        self.assertIn("sbom: true", workflow)
        self.assertIn("openfoam-engine-f35-index.json", workflow)
        self.assertIn("openfoam-engine-f35-sbom.json", workflow)
        self.assertIn('printf \'{"auths":{}}\\n\'', workflow)
        self.assertIn("openfoam-engine-f35-anonymous-smoke.json", workflow)
        self.assertIn("cmp openfoam-engine-f35-smoke.json", workflow)
        self.assertNotIn(":latest", workflow)


if __name__ == "__main__":
    unittest.main()
