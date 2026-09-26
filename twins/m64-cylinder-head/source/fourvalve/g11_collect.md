# G11 bounded private collection

Stop the campaign and its telemetry producer before packing. The collector reads
outputs; it does not stop jobs, rent machines, transfer files, or authorize parts.

On the owned compute instance, after copying `g11_collect.py` there:

```sh
python3 /workspace/m64-g11/g11_collect.py pack \
  --root /workspace/m64-g11 \
  --archive /workspace/m64-g11/g11-collection.tar.xz --xz-preset 1
```

Use the returned SHA-256 and byte count to preflight **one** transfer. The default
archive ceiling is **1,990,000,000 bytes**, reserving 10 MB of the 2 GB allocation
for previous traffic and metadata. If previous traffic is larger, lower
`--max-bytes`; do not split archives to evade the cumulative allocation.

After transfer to a private local directory, run from the repository:

```sh
python3 twins/m64-cylinder-head/source/fourvalve/g11_collect.py verify \
  --archive /absolute/private/path/g11-collection.tar.xz \
  --sha256 SHA256_RETURNED_BY_PACK
```

Verification streams and hashes every retained file without unpacking the large
fields. It rejects unexpected paths, links, duplicate members, changed content,
and cap violations. The conservative limits remain 2 GiB per retained file and
12 GiB of uncompressed content. Failed verification is not a collected result.

All results, including DAT/INP/MSH/DOF/FRD and failed-case logs, are retained except
the exact names `matrix.sti` and `matrix.mas`. Root files use an explicit runtime
allowlist; virtual environments, input archives, account metadata, and credential
files are excluded. `environment.txt` is the job's package-version list, not an
environment-variable dump. The archive inventory records size, SHA-256, and the
reason for every retained/omitted result file. Original result hashes are unchanged.

**This is not a directly resumable checkpoint.** Reconstruct omitted matrices
from the retained `matrix.inp` using the pinned CalculiX runtime and check their
original fingerprints before checkpoint reuse or a fresh CUDA residual check.
XZ preset 1 with a 256 MiB dictionary and case/suffix/name ordering was selected
for lossless packing; no mechanical acceptance threshold is changed.

Check: `python3 -m unittest discover -s tests -p test_m64_g11_collect.py -v`.
