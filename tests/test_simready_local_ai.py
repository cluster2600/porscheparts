import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SimReadyLocalAiImageTests(unittest.TestCase):
    def test_image_pins_model_runtime_and_physicsnemo(self):
        dockerfile = (ROOT / "containers/simready-local-ai.Dockerfile").read_text()
        self.assertIn("VLLM_VERSION=0.8.5.post1", dockerfile)
        self.assertIn("PHYSICSNEMO_VERSION=2.2.0", dockerfile)
        self.assertIn("Qwen/Qwen2.5-VL-7B-Instruct", dockerfile)
        self.assertIn("LOCAL_VLM_REVISION=cc594898137f460bfe9f0759e9844b3ce807cfb5", dockerfile)
        self.assertIn('test -f "${LOCAL_VLM_PATH}/LICENSE.apache-2.0"', dockerfile)

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


if __name__ == "__main__":
    unittest.main()
