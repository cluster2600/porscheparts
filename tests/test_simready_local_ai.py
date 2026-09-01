import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SimReadyLocalAiImageTests(unittest.TestCase):
    def test_image_pins_model_runtime_and_physicsnemo(self):
        dockerfile = (ROOT / "containers/simready-local-ai.Dockerfile").read_text()
        self.assertIn("VLLM_VERSION=0.19.0", dockerfile)
        self.assertIn("VLLM_TORCH_VERSION=2.10.0", dockerfile)
        self.assertIn("VLLM_TORCHVISION_VERSION=0.25.0", dockerfile)
        self.assertIn("VLLM_TORCHAUDIO_VERSION=2.10.0", dockerfile)
        self.assertIn("https://download.pytorch.org/whl/cu129", dockerfile)
        self.assertIn("assert cuda >= (12, 8)", dockerfile)
        self.assertNotIn("TRANSFORMERS_VERSION", dockerfile)
        self.assertIn("PHYSICSNEMO_VERSION=2.2.0", dockerfile)
        self.assertIn("TORCH_VERSION=2.8.0", dockerfile)
        self.assertIn("https://download.pytorch.org/whl/cu128", dockerfile)
        self.assertIn("import torch; cuda = tuple", dockerfile)
        self.assertIn("BUILD123D_VERSION=0.11.1", dockerfile)
        self.assertIn("CADQUERY_VERSION=2.8.0", dockerfile)
        self.assertIn('"nvidia-physicsnemo[sym]==${PHYSICSNEMO_VERSION}"', dockerfile)
        self.assertIn("Qwen/Qwen2.5-VL-7B-Instruct", dockerfile)
        self.assertIn("LOCAL_VLM_REVISION=cc594898137f460bfe9f0759e9844b3ce807cfb5", dockerfile)
        self.assertIn("HF_HUB_DISABLE_XET=1", dockerfile)
        self.assertIn("max_workers=2", dockerfile)
        self.assertEqual(dockerfile.count("ADD --checksum=sha256:"), 5)
        self.assertIn("ffmpeg", dockerfile)
        self.assertIn('test -f "${LOCAL_VLM_PATH}/LICENSE.apache-2.0"', dockerfile)
        self.assertIn('"torch==${VLLM_TORCH_VERSION}"', dockerfile)
        self.assertIn('"torchvision==${VLLM_TORCHVISION_VERSION}"', dockerfile)
        self.assertIn('"torchaudio==${VLLM_TORCHAUDIO_VERSION}"', dockerfile)

    def test_vast_ready_gate_checks_the_full_local_ai_image(self):
        dockerfile = (ROOT / "containers/simready-local-ai.Dockerfile").read_text()
        onstart = (ROOT / "containers/simready-vast-onstart.sh").read_text()
        workflow = (ROOT / ".github/workflows/containers.yml").read_text()
        self.assertIn(
            "COPY containers/simready-vast-onstart.sh /usr/local/bin/simready-vast-onstart",
            dockerfile,
        )
        self.assertIn("smoke-test.sh simready-local-ai", onstart)
        self.assertNotIn("smoke-test.sh simready >", onstart)
        self.assertIn("simready-services start", onstart)
        self.assertIn("simready-services status", onstart)
        self.assertLess(onstart.index("simready-services status"), onstart.index('touch "${WORKSPACE}/READY"'))
        self.assertIn("Verify published local AI manifest limits", workflow)
        self.assertIn(".Image.OS}}/{{.Image.Architecture", workflow)
        self.assertIn("max) < 5000000000", workflow)
        self.assertIn("add) < 45000000000", workflow)

    def test_both_agents_use_the_local_endpoint(self):
        config = (ROOT / "containers/simready-local-ai-supervisord.conf").read_text()
        local_endpoint = 'http://127.0.0.1:8000/v1'
        self.assertIn(f'MA_VLM_NIM_BASE_URL="{local_endpoint}"', config)
        self.assertIn(f'MA_LLM_NIM_BASE_URL="{local_endpoint}"', config)
        self.assertIn(f'PA_VLM_NIM_BASE_URL="{local_endpoint}"', config)
        self.assertNotIn("NVIDIA_API_KEY", config)

    def test_local_mode_does_not_require_remote_credentials(self):
        services = (ROOT / "containers/simready-services.sh").read_text()
        local_branch = services.index('if [ "${SIMREADY_LOCAL_AI:-0}" = "1" ]')
        credential_load = services.index("load_credentials", local_branch)
        remote_branch = services.index("else", local_branch)
        self.assertGreater(credential_load, remote_branch)

    def test_live_smoke_covers_multimodal_input(self):
        smoke = (ROOT / "containers/simready-local-ai-smoke.sh").read_text()
        config = (ROOT / "containers/simready-local-ai-supervisord.conf").read_text()
        self.assertIn("data:image/png;base64", smoke)
        self.assertIn("image_url", smoke)
        self.assertIn("--limit-mm-per-prompt image=20", config)
        self.assertIn("--max-model-len 32768", config)


if __name__ == "__main__":
    unittest.main()
