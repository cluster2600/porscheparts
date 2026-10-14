"""La publication GHCR reste limitée à la recette et aux contrôles CPU."""
from pathlib import Path
import re
import unittest


class QwenTrainingImageWorkflowTest(unittest.TestCase):
    def test_publication_boundaries(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root/'.github/workflows/qwen-picogk-training-vast-image.yml').read_text()
        trigger = workflow.split('concurrency:', 1)[0]
        self.assertIn('branches:\n      - codex/qwen-picogk-training-image\n', trigger)
        self.assertNotIn('workflow_dispatch:', workflow)
        self.assertNotIn('pull_request:', workflow)
        self.assertNotIn('- main', trigger)
        self.assertIn('permissions:\n  contents: read\n  packages: write\n', workflow)
        self.assertEqual(re.findall(r'secrets\.([A-Za-z_][A-Za-z_0-9]*)', workflow), ['GITHUB_TOKEN'])
        self.assertIn('ghcr.io/cluster2600/qwen-picogk-training-vast', workflow)
        self.assertIn('IMAGE_TAG: ${{ github.sha }}', workflow)
        self.assertIn('load: true\n          push: false', workflow)
        self.assertLess(workflow.index('Verify offline CPU smoke'), workflow.index('docker push'))
        self.assertIn('docker pull --platform linux/amd64 "${pinned_ref}"', workflow)
        self.assertIn('imagetools inspect --raw "${pinned_ref}"', workflow)
        self.assertIn('--network none --read-only', workflow)
        self.assertIn('gpu_tested:false,vast_ssh_tested:false', workflow)
        self.assertNotIn('openbao', workflow)
        self.assertNotIn('--gpus', workflow)
        self.assertNotIn('vllm', workflow)
        self.assertNotIn('ports:', workflow)
        for action in re.findall(r'uses:\s+(\S+)', workflow):
            self.assertRegex(action, r'^[^@]+@[0-9a-f]{40}$')
        allowed = (root/'containers/qwen-picogk-training-vast/Dockerfile.dockerignore').read_text()
        self.assertIn('\n**\n', '\n'+allowed)
        self.assertNotIn('!tests/', allowed)
        self.assertNotIn('!data/', allowed)


if __name__ == '__main__':
    unittest.main()
