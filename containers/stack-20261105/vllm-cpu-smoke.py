"""Check packaged inference runtime without weights, network or GPU claims."""
import importlib.metadata as metadata
import json
import subprocess
import sys
import torch
import vllm
from transformers import Qwen2Config

subprocess.run([sys.executable,'/opt/stack/vllm-dependency-check.py'], check=True)

assert metadata.version('vllm').split('+')[0] == '0.33.0'
assert vllm.__version__.split('+')[0] == '0.33.0'
assert torch.__version__.split('+')[0] == '2.14.0'
matrix = torch.tensor([[1., 2.], [3., 4.]])
torch.testing.assert_close(matrix @ matrix, torch.tensor([[7., 10.], [15., 22.]]))
assert Qwen2Config(hidden_size=32, num_attention_heads=4).hidden_size == 32
print(json.dumps({'status':'VLLM_CPU_PACKAGE_WITNESS_PASS',
                  'versions':{n:metadata.version(n) for n in ['vllm','torch','transformers']},
                  'cuda_build':torch.version.cuda, 'gpu_serving_tested':False,
                  'model_weights_loaded':False}))
