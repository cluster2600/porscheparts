# PySLM runtime with controlled domains

This directory keeps the generator and the installation used by the cache of
the part's 1,034 layers. The versions and the four corrected PySLM modules
are bound by digest in [upstream.json](upstream.json). The installer
refuses an existing directory, checks the patch and the installed files,
verifies the dependencies and slices a 20 × 10 mm witness.

Installation on macOS arm64 with Python 3.11:

```sh
python3.11 parts/993-eng-carrier-0001/source/process-coverage-20261016/setup_pyslm.py \
  work/part-workflow/runtimes/pyslm-new
```

The [independent reinstallation receipt](../process-slicing-20261016/pyslm-reinstall-validation.json)
confirms the runtime actually reproduced. The [layer cache](../process-cache-20261016/README.md)
uses this frozen generator; the skin and contact corrections remain in
`process-skins-20261016` to preserve its digests.

The generator alone does not constitute an admitted complete preparation: the
historical generation of the carrier supports was refused. The additional
checks of all regions, skins, grids, contacts, collisions and scan paths
remain necessary. No translation into a machine-specific build file is
executed here.

PySLM is kept at revision
`8fa03f1eb98b1fbc8e617eb3119d669f356a2f0b`, under LGPL-2.1, with its
[licence](LICENSE.pyslm), its patch and the locked list of dependencies.
The historical runtime of `process-20261016` remains separate.

The patch is kept byte for byte: `git diff --check` notably flags the
whitespace on the empty context lines of this diff file. Removing it would
modify the pinned input of the reproduced installation.
