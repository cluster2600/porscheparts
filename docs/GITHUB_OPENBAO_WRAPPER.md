# OpenBao-bounded GitHub wrapper

`deploy/openbao/openbao-github` only pushes the current `codex/*` branch
of the `cluster2600/3dprinting993` repository and only triggers the two
explicitly allowed Vast F40/F41 workflows. It reuses the AppRole already
provisioned for `openbao-ghcr`; no token is added to the repository or to the
command line.

The wrapper disables the macOS keychain Git helper for its subprocess.
It passes the HTTP authentication header to Git through ephemeral environment
configuration, with no URL containing a secret, defensively masks the value
before any error and always revokes the OpenBao session token.

## Installation and checks

```zsh
cd /Users/maxime/projects/3dprinting993
install -m 0755 deploy/openbao/openbao-github \
  /Users/maxime/.local/bin/openbao-github
rehash
openbao-github --check
openbao-github --auth-check
```

`--check` reads no secret. `--auth-check` only checks the fixed repository and
requires the GitHub identity to return the `push` permission.

## Allowed operations

The worktree must be clean before a push:

```zsh
openbao-github push-current
```

Once the branch is published, a workflow can be triggered by its exact name
and the same branch:

```zsh
openbao-github dispatch 917-engine-wave-f40-vast-image.yml \
  codex/917-f40-vast-runtime-hardening

openbao-github runs 917-engine-wave-f40-vast-image.yml \
  codex/917-f40-vast-runtime-hardening

# Rebuild and publish only the large local SimReady image.
# The wrapper fixes the inputs image=simready-local-ai and push=true.
openbao-github publish-simready-local-ai \
  codex/917-f40-vast-runtime-hardening
```

The second allowed workflow is
`917-component-factory-f41-vast-image.yml`. No arbitrary workflow, `main`
branch, fork, other repository, PR creation or merge is exposed by this
wrapper.

## Trust boundary

A successful push proves neither that GitHub Actions is green, nor that a GHCR
digest is public, nor that Vast can establish an SSH session. These states are
checked separately before any rental. The wrapper sends no scan, manual,
vehicle identifier or private data: only Git objects already committed
on a `codex/*` branch can be pushed.
