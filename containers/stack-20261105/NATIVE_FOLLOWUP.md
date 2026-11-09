# Native stack follow-up

This directory records additive runtime work for issues #404–#407. Historical
image recipes and locks remain unchanged. A local image ID is not a published
registry digest, and a CPU package control does not qualify GPU execution.

## vLLM 0.33.0

The digest-pinned upstream image contains an unrequired experimental
`opentelemetry-exporter-otlp-common==0.66b2` package requiring SDK 1.45.2.
LMCache 0.5.6 caps the API at 1.40.0, and the installed stable exporters require
the corresponding SDK. Inspection of every installed distribution's declared
requirements found no dependent of the experimental exporter. Remove only that
package; retain the stable `opentelemetry-exporter-otlp-proto-common==1.40.0`.
The initial attempt to downgrade the experimental package to 0.61b0 failed
because that release does not exist. Its failed receipt is retained privately.

The remaining `pip check` mismatch is the exact NCCL override documented in
[vLLM's upstream Dockerfile](https://github.com/vllm-project/vllm/blob/v0.33.0/docker/Dockerfile).
The dependency guard requires the recorded versions and exact diagnostic,
rejecting additional mismatches, stderr, changed versions and unexpected exit
codes. It reports `pip_check_clean=false`; it does not hide the override.

From the repository root, on native Linux AMD64:

```sh
docker build --platform linux/amd64 -f containers/stack-20261105/vllm-runtime.Dockerfile -t porscheparts/vllm-runtime:stack-20261105 .
docker run --rm --network none --cpus 2 --memory 4g porscheparts/vllm-runtime:stack-20261105
PYTHONPATH=tests python3 -m unittest -v test_vllm_dependency_check
```

`vllm-native-validation.json` records the successful native build and bounded
offline run, image identity, source hashes, receipt hashes and actual reports.
The smoke imports vLLM, checks CPU matrix multiplication and creates a small
Qwen configuration. It loads no weights and does not test serving, training,
CUDA kernels or GPU collectives. Full build and smoke logs remain in the private
`stack-followup-20261107/receipts/vllm-runtime.gAHd2s` artifact directory.
