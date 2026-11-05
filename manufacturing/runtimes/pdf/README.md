# PDF runtime for the workshop guide

This lock targets **CPython 3.12 on macOS arm64**. The fresh venv was verified with
CPython **3.12.14**, ReportLab **4.4.9**, Pillow **12.3.0** and
charset-normalizer **3.5.2**. The three base dependencies are fully
pinned; no ReportLab extra is enabled.

The wheel names, URLs and SHA256 values were checked against the primary PyPI
metadata of [ReportLab](https://pypi.org/project/reportlab/4.4.9/),
[Pillow](https://pypi.org/project/pillow/12.3.0/) and
[charset-normalizer](https://pypi.org/project/charset-normalizer/3.5.2/), then
against the downloaded bytes. [wheels.json](wheels.json) keeps these identities.
The native wheels are `cp312`, Pillow being limited to `macosx_11_0_arm64` and
charset-normalizer supplied as `macosx_10_13_universal2`.

From the repository root, with Python 3.12 installed and a **fresh** directory:

```sh
python3.12 -c 'import platform,sys; assert sys.version_info[:2] == (3,12) and sys.platform == "darwin" and platform.machine() == "arm64"'
python3.12 -m venv work/part-workflow/runtimes/pdf-base-001
work/part-workflow/runtimes/pdf-base-001/bin/python -m pip --isolated install \
  --index-url https://pypi.org/simple --only-binary=:all: --require-hashes \
  -r manufacturing/runtimes/pdf/requirements-macos-arm64-python312.lock.txt
work/part-workflow/runtimes/pdf-base-001/bin/python -m pip --isolated check
work/part-workflow/runtimes/pdf-base-001/bin/python -B -m unittest \
  tests.test_part_workflow_guide -v
```

For an offline installation, place the three exact wheels from
`wheels.json` in a directory and replace `--index-url ...` with
`--no-index --find-links /chemin/roues`. This is the mode that was run after
the independent download and verification of the SHAs. No existing
runtime was modified.

The value to supply to the recipe for `pdf_python` is
`work/part-workflow/runtimes/pdf-base-001/bin/python`. This directory contains the
venv; its `runtime.json` is a local installation receipt, not an installer.
The Python binary is not included in this package lock.

[results.json](results.json) keeps the verification performed: `pip check`,
the two guide tests and a real small **synthetic** PDF with a PNG image.
The guide tests deliberately simulate the PDF export; the separate witness
actually exercises ReportLab and Pillow. It is neither the carrier dossier,
nor an admission of its supports or of its manufacture.

The existing renderer uses system Arial when present and Helvetica
otherwise. The digests of the fonts actually available appear in the
local receipt. The lock does not distribute system fonts and does not guarantee a
byte-identical PDF across machines or export dates. No frozen guide
script was modified.
