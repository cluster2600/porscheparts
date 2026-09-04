# ovrtx-render-service Report

- Asset: `/workspace/f37-simready/output/final/f37-final.usdc`
- Output image: `/workspace/f37-simready/output/final/f37-final.png`
- Renderer endpoint kind: `local-service`
- Renderer auth mode: `none`
- Passed: `True`
- Next step: `inspect-render-output`

## Checks

- `PASS` `asset_exists`: Asset path exists
- `PASS` `supported_usd_extension`: Asset uses a supported USD extension
- `PASS` `render_endpoint_available`: Using renderer endpoint http://127.0.0.1:8001/render
- `PASS` `render_endpoint_from_cli`: Resolved renderer endpoint from cli
- `PASS` `render_token_not_required`: Renderer endpoint does not require a bearer token before request
- `PASS` `openusd_stage_opened`: USD stage opened
- `PASS` `renderable_meshes_found`: Renderable mesh prims found
- `PASS` `render_stage_prepared`: Prepared composition-preserving, camera-fit render stage
- `PASS` `renderer_returned_png`: Renderer returned PNG data
- `PASS` `output_png_written`: Wrote /workspace/f37-simready/output/final/f37-final.png
- `PASS` `output_png_non_uniform`: Output PNG has visible pixel variation
