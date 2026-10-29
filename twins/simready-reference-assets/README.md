# NVIDIA SimReady reference assets

Two external assets exercise our OpenUSD pipeline:
`engineComponent_crankshaft_b01` (generic crankshaft) and `socket_b01`
(workshop socket). They provide reference packages for testing references,
textures, materials and physics variants independently of our private scans.

This directory defines no Porsche parts. It provides no reconstruction
measurements, measured interfaces or qualified material models for 993/M64/917
parts. NVIDIA properties are not transferred into the parts catalogue.

## Provenance and attribution

NVIDIA, **SimReady Assets**, assets `engineComponent_crankshaft_b01` and
`socket_b01`, licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Source: [NVIDIA dataset](https://huggingface.co/datasets/nvidia/simready-assets/tree/b925ca4954fea51af7ef03f5668ea0d62a207af7).
Original packages remain unmodified. The presentation scene and inspection
scripts are additions by this project.

`assets.lock.json` pins the revision and upstream hashes of all 140 files,
including each package's license and dependencies. The provenance record is
[`src-nvidia-simready-reference-assets.json`](../../catalog/sources/src-nvidia-simready-reference-assets.json).
Downloaded models and generated results remain under `work/`, outside Git.
Keep this attribution and the licenses when sharing a scene or render.

## Run from the repository root

```bash
python3 twins/simready-reference-assets/fetch.py
python3 twins/simready-reference-assets/fetch.py --offline

python3 -m venv work/simready-reference-assets-tools
work/simready-reference-assets-tools/bin/python -m pip install usd-core==26.5
work/simready-reference-assets-tools/bin/python twins/simready-reference-assets/inspect_assets.py

python3 -m unittest discover -s tests -p test_simready_reference_assets.py
```

Downloads are public and use no Hugging Face token. An existing file with
incorrect contents causes a failure rather than being silently replaced.
`download-receipt.json` also records local SHA-256 hashes.

Inspection opens the USD files and checks dependencies, meshes, bounds and
composition errors for each root variant choice separately. It does not test
every combination of variants. Temporary selections are written only to a
session layer. Historical NVIDIA validation failures remain in the report.

Outputs under `work/simready-reference-assets/`:

- `inspection.json`: OpenUSD checks and explicit limitations;
- `reference-gallery.usda`: two spaced references, in meters with Z up;
- `download-receipt.json`: downloaded-file integrity.

The gallery can be used in the existing Omniverse workflow. Move both packages
with it to preserve relative paths. Rendering MDL dependencies requires an
MDL-capable renderer.

## Results recorded on 28 October 2026

140 files, 358,547,572 bytes, verified against upstream hashes and checked again
offline. With OpenUSD 26.5, both assets and the gallery compose without errors
or missing dependencies. Inspection includes instance-proxy meshes: one for
the crankshaft and two for the socket. All six variant choices per asset were
opened separately without composition errors.
The record is preserved in [`inspection-evidence.json`](inspection-evidence.json).
Historical failures recorded in NVIDIA layers are retained per layer, so the
same failure may appear more than once.

Both integrity tests and the source validator passed. In the original working
checkout, `make check` ran 925 tests, with seven skipped tests and one error in
`test_pet_993_porschefanatics_crosswalk.setUpClass`:
`ContractError("source_part_record_count")`. That check concerns files not
modified by this integration. The original local log is
`work/simready-reference-assets-make-check.log`.

## Separate physics validation

Successful OpenUSD loading does not validate contacts, dynamics or RTX
rendering. No physics solver, GPU render or CFD/FEA calculation runs here.
NVIDIA's `Package` conformance report concerns packaging, not manufacturing
qualification.

For a future profile check, use the wrapper already included in our SimReady
image: `containers/simready-profile-validate.sh`. Select a profile and version
available in that image, check that they match the asset metadata, and retain
the report. Do not treat a historical positive result as current validation.
