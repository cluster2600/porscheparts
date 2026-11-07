"""Fail on every pip mismatch except vLLM's exact documented NCCL override."""
import importlib.metadata as metadata
import json
import subprocess
import sys

assert metadata.version('torch') == '2.14.0+cu130'
assert metadata.version('nvidia-nccl-cu13') == '2.31.2'
assert metadata.version('lmcache') == '0.5.6'
assert metadata.version('opentelemetry-api') == '1.40.0'
assert 'opentelemetry-exporter-otlp-common' not in {
    d.metadata['Name'].lower() for d in metadata.distributions()}
assert metadata.version('opentelemetry-exporter-otlp-proto-common') == '1.40.0'
check = subprocess.run([sys.executable,'-m','pip','check'],capture_output=True,text=True)
expected = 'torch 2.14.0+cu130 has requirement nvidia-nccl-cu13==2.30.7; platform_system == "Linux", but you have nvidia-nccl-cu13 2.31.2.'
assert check.returncode == 1 and check.stdout.strip() == expected and not check.stderr, (
    check.returncode, check.stdout, check.stderr)
print(json.dumps({'status':'DEPENDENCIES_MATCH_WITH_EXPLICIT_UPSTREAM_NCCL_OVERRIDE',
                  'pip_check_clean':False, 'accepted_metadata_mismatch':expected,
                  'reason':'vLLM 0.33.0 Dockerfile pins NCCL 2.31.2 for DeepEPv2 GDA over EFA',
                  'source':'https://github.com/vllm-project/vllm/blob/v0.33.0/docker/Dockerfile',
                  'gpu_collectives_tested':False}))
