# CAD to SimReady Preflight

- Status: `blocked`
- Platform: `darwin`
- Manifest: `${PROJECT_ROOT}/work/917-integrated-virtual-f33/omniverse/preflight.json`

## Runtimes

- `asset_validator`: `blocked` - omni_asset_validate CLI and omni.asset_validator module are unavailable
- `content_agents`: `blocked` - Content Agents services are not healthy and deployment was not requested
- `git_lfs`: `ready` - Git LFS is available
- `openusd_python`: `blocked` - OpenUSD Python APIs are not importable
- `repo_python`: `skipped` - no pyproject.toml found near cwd or preflight script
- `request`: `ready` - request inputs are ready
- `simready_validate`: `blocked` - SimReady Foundation checkout is missing
- `usd_convert_cad`: `blocked` - usd-convert-cad checkout is missing

## Services

- `material`: `blocked` - http://localhost:8100
- `ovrtx`: `blocked` - http://localhost:8001
- `physics`: `blocked` - http://localhost:8200

## Blockers

- asset_validator: omni_asset_validate CLI and omni.asset_validator module are unavailable
- content_agents: Content Agents services are not healthy and deployment was not requested
- openusd_python: OpenUSD Python APIs are not importable
- simready_validate: SimReady Foundation checkout is missing
- usd_convert_cad: usd-convert-cad checkout is missing
- material: material health endpoint did not respond
- ovrtx: ovrtx health endpoint did not respond
- physics: physics health endpoint did not respond
