import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SimReadyLocalAiImageTests(unittest.TestCase):
    def test_image_pins_model_runtime_and_physicsnemo(self):
        dockerfile = (ROOT / "containers/simready-local-ai.Dockerfile").read_text()
        self.assertIn("VLLM_VERSION=0.26.0", dockerfile)
        self.assertIn("VLLM_TORCH_VERSION=2.11.0", dockerfile)
        self.assertIn("VLLM_TORCHVISION_VERSION=0.26.0", dockerfile)
        self.assertIn("VLLM_TORCHAUDIO_VERSION=2.11.0", dockerfile)
        self.assertIn("https://download.pytorch.org/whl/cu129", dockerfile)
        self.assertGreaterEqual(dockerfile.count('torch.version.cuda == "12.9"'), 2)
        self.assertEqual(dockerfile.count('actual["cuda"] == "12.9"'), 1)
        self.assertNotIn("TRANSFORMERS_VERSION", dockerfile)
        self.assertIn("PHYSICSNEMO_VERSION=2.2.0", dockerfile)
        self.assertIn("TORCH_VERSION=2.10.0", dockerfile)
        self.assertIn("TORCHVISION_VERSION=0.25.0", dockerfile)
        self.assertNotIn("cu128", dockerfile)
        self.assertIn("torch.version.cuda == \"12.9\"", dockerfile)
        self.assertIn("COPY containers/simready-physicsnemo-constraints.txt", dockerfile)
        self.assertIn("--constraint /opt/build/physicsnemo-constraints.txt", dockerfile)
        self.assertIn("/opt/venv/bin/pip check", dockerfile)
        self.assertIn("/opt/local-ai/bin/pip check", dockerfile)
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

        constraints = (ROOT / "containers/simready-physicsnemo-constraints.txt").read_text()
        self.assertIn("torch==2.10.0", constraints)
        self.assertIn("torchvision==0.25.0", constraints)

    def test_vast_ready_gate_checks_the_full_local_ai_image(self):
        dockerfile = (ROOT / "containers/simready-local-ai.Dockerfile").read_text()
        onstart = (ROOT / "containers/simready-vast-onstart.sh").read_text()
        workflow = (ROOT / ".github/workflows/containers.yml").read_text()
        self.assertIn(
            "COPY containers/simready-vast-onstart.sh /usr/local/bin/simready-vast-onstart",
            dockerfile,
        )
        self.assertIn(
            "COPY containers/physicsnemo-gpu-smoke.py /usr/local/bin/physicsnemo-gpu-smoke",
            dockerfile,
        )
        base_dockerfile = (ROOT / "containers/simready.Dockerfile").read_text()
        self.assertIn(
            "COPY containers/simready-sshd-runtime-wrapper.sh /usr/local/bin/simready-sshd-runtime-wrapper",
            base_dockerfile,
        )
        self.assertIn(
            "COPY containers/simready-nvidia-auth-check.sh /usr/local/bin/simready-nvidia-auth-check",
            base_dockerfile,
        )
        self.assertIn(
            "COPY containers/simready-profile-validate.sh /usr/local/bin/simready-profile-validate",
            base_dockerfile,
        )
        self.assertIn("/usr/local/bin/simready-nvidia-auth-check \\", base_dockerfile)
        self.assertIn("/usr/local/bin/simready-profile-validate \\", base_dockerfile)
        self.assertIn("mv /usr/sbin/sshd /usr/lib/openssh/sshd.real", base_dockerfile)
        self.assertIn("rm -f /etc/ssh/ssh_host_*_key", base_dockerfile)
        self.assertIn("/root/.no_auto_tmux", base_dockerfile)
        self.assertIn(
            "ln -s /usr/local/bin/simready-sshd-runtime-wrapper /usr/sbin/sshd",
            base_dockerfile,
        )
        self.assertIn("smoke-test.sh simready-local-ai", onstart)
        self.assertIn('"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}"', onstart)
        self.assertIn("/usr/local/bin/physicsnemo-gpu-smoke", onstart)
        self.assertLess(onstart.index("physicsnemo-gpu-smoke"), onstart.index('mv -f -- "${READY_TMP}" "${READY}"'))
        self.assertNotIn("smoke-test.sh simready >", onstart)
        self.assertIn("simready-services start", onstart)
        self.assertIn("simready-services status", onstart)
        self.assertLess(onstart.index("simready-services status"), onstart.index('mv -f -- "${READY_TMP}" "${READY}"'))
        self.assertIn("/run/sshd/simready-runtime-host-keys.ready", onstart)
        self.assertIn("/root/.no_auto_tmux", onstart)
        self.assertIn("target_1600_ch_validated\": false", onstart)
        self.assertIn("Verify published local AI manifest limits", workflow)
        self.assertIn(".Image.OS}}/{{.Image.Architecture", workflow)
        self.assertIn("max) < 5000000000", workflow)
        self.assertIn("add) < 45000000000", workflow)
        self.assertIn("application/vnd.oci.image.manifest.v1+json", workflow)
        local_build = workflow[
            workflow.index("- name: Build large local AI image from Docker store") :
            workflow.index("- name: Verify published local AI manifest limits")
        ]
        self.assertNotIn("simready-local-ai:latest", local_build)
        self.assertIn("- name: Promote verified image", workflow)
        self.assertIn("docker buildx imagetools create", workflow)
        self.assertIn("--prefer-index=false", workflow)
        self.assertIn('test "$latest_digest" = "$expected_digest"', workflow)
        self.assertIn("Verify anonymous digest pull", workflow)
        self.assertIn(
            'DOCKER_CONFIG="${anonymous_config}" docker pull --platform linux/amd64',
            workflow,
        )
        self.assertIn("group: container-publication-${{ matrix.image }}", workflow)
        self.assertIn("id: standard_build", workflow)
        self.assertIn("steps.standard_build.outputs.digest", workflow)
        self.assertIn("id: local_ai_build", workflow)
        self.assertIn('--metadata-file "$metadata_file"', workflow)
        self.assertIn("steps.local_ai_build.outputs.digest", workflow)
        self.assertIn("--platform linux/amd64", workflow)
        self.assertLess(
            workflow.index("- name: Verify anonymous digest pull"),
            workflow.index("- name: Promote verified image"),
        )
        self.assertLess(
            workflow.index("- name: Verify published local AI manifest limits"),
            workflow.index("- name: Verify anonymous digest pull"),
        )
        self.assertNotIn("Pull and smoke test the published image", workflow)
        self.assertIn("/usr/local/bin/simready-sshd-runtime-smoke", workflow)
        anonymous = workflow[
            workflow.index("- name: Verify anonymous digest pull") :
            workflow.index("- name: Promote verified image")
        ]
        self.assertIn("docker image rm -f", anonymous)
        self.assertIn("docker buildx prune --all --force", anonymous)
        self.assertIn("docker system prune --all --force --volumes", anonymous)
        self.assertIn("printf '{}\\n'", anonymous)
        self.assertLess(
            anonymous.index('DOCKER_CONFIG="${anonymous_config}" docker pull'),
            anonymous.index('DOCKER_CONFIG="${anonymous_config}" docker run'),
        )

        ssh_wrapper = (ROOT / "containers/simready-sshd-runtime-wrapper.sh").read_text()
        self.assertIn("/usr/bin/flock -x 9", ssh_wrapper)
        self.assertIn("/usr/bin/ssh-keygen -A", ssh_wrapper)
        self.assertIn("simready-runtime-host-keys.ready", ssh_wrapper)
        self.assertIn('if [ "${argument}" = "-R" ]', ssh_wrapper)

        ssh_smoke = (ROOT / "containers/simready-sshd-runtime-smoke.sh").read_text()
        self.assertIn("/usr/bin/flock -x 8", ssh_smoke)
        self.assertIn('kill -0 "${first}"', ssh_smoke)
        self.assertIn('kill -0 "${second}"', ssh_smoke)
        self.assertIn("simready_ephemeral_sshd_concurrency_smoke_passed", ssh_smoke)

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
        self.assertIn("--limit-mm-per-prompt '{\"image\":20}'", config)
        self.assertIn("--max-model-len 32768", config)
        self.assertEqual(smoke.count('torch.version.cuda == "12.9"'), 1)
        self.assertEqual(smoke.count('actual["cuda"] == "12.9"'), 1)
        self.assertIn('actual["runtime"].split("+", 1)[0] == "0.26.0"', smoke)
        self.assertIn('actual["torch"].split("+", 1)[0] == "2.11.0"', smoke)
        self.assertIn('actual["torchaudio"].split("+", 1)[0] == "2.11.0"', smoke)
        self.assertIn('actual["torchvision"].split("+", 1)[0] == "0.26.0"', smoke)
        self.assertIn("/opt/local-ai/bin/pip check", smoke)
        self.assertIn('"${PHYSICSNEMO_PYTHON:-/opt/venv/bin/python}" -m pip check', smoke)
        self.assertIn('VLLM_USE_FLASHINFER_SAMPLER="0"', config)
        self.assertIn('PATH="/opt/local-ai/bin:', config)
        self.assertIn('LD_LIBRARY_PATH="/opt/local-ai/lib/python3.12/site-packages/torch/lib:', config)
        self.assertIn("VLLM_LIBRARY_PATH=", smoke)
        self.assertIn('env LD_LIBRARY_PATH="${VLLM_LIBRARY_PATH}" /opt/local-ai/bin/python', smoke)
        self.assertIn('actual["distribution"].split("+", 1)[0] == "0.26.0"', smoke)
        self.assertNotIn('== "0.26.0+cu129"', smoke)


if __name__ == "__main__":
    unittest.main()
