# GitHub access from OpenClaw on Kali2

`openclaw-github.py` provides explicit reads and a standard Git helper.
It does not replace the whole `gh` CLI. The two **private** repositories and
their IDs, confirmed by an authenticated check, are the only ones allowed:

| Repository | GitHub ID |
|---|---:|
| `cluster2600/porscheparts` | `1349420480` |
| `cluster2600/porschefanatics.com` | `1336775701` |

The Mac keeps the existing OpenBao identity. The dispatcher loads only
`/Users/maxime/.local/bin/openbao-github`, whose SHA-256 is pinned to
`d71cf774a0f0cba1eb2e199db38438c11a5df71d68212ea37038d45820c5b052`.
It reuses its login, its authorised read of `secrets/data/github` and its
session revocation; no credentials file is copied to Kali2.
Any change to the wrapper requires a review and a new explicit pin.

## Controlled installation

The reverse transport already prepared listens only on
`127.0.0.1:2220` on Kali2 and reaches SSH on the Mac. Install the source
as `/Users/maxime/.local/bin/openclaw-github-bridge` on the Mac and
`/home/lolman/.local/bin/openclaw-github` on Kali2. The Mac already has
`/opt/homebrew/bin/gh`; the Kali2 helper uses Python and SSH.

Authorise only the **dedicated public key** from
`/home/lolman/.ssh/id_openclaw_github` in the Mac's `authorized_keys`:

```text
restrict,from="127.0.0.1",command="/usr/local/bin/python3 /Users/maxime/.local/bin/openclaw-github-bridge --dispatch" ssh-ed25519 CLE_PUBLIQUE_DEDIEE
```

Keep the Python shebang executable and do not open a shell with this key.
Pin the Mac's public SSH host key, verified out of band, in
`/home/lolman/.ssh/openclaw_github_known_hosts`, under the alias
`openclaw-github-mac`. The source enforces `StrictHostKeyChecking=yes`,
`IdentitiesOnly=yes`, no forwarded agent, the loopback destination and the
fixed command `openclaw-github`. It refuses any other original SSH command.
The `restrict` and `command` mechanisms are those of [OpenSSH](https://man.openbsd.org/sshd.8#AUTHORIZED_KEYS_FILE_FORMAT).

## Reads

```sh
openclaw-github check cluster2600/porscheparts
openclaw-github repo cluster2600/porschefanatics.com
openclaw-github file cluster2600/porscheparts README.md --ref main
openclaw-github branches cluster2600/porscheparts
openclaw-github prs cluster2600/porscheparts
openclaw-github pr cluster2600/porscheparts 92
openclaw-github issues cluster2600/porschefanatics.com
openclaw-github runs cluster2600/porscheparts
```

The outputs are GitHub's JSON responses, treated as external data.
`file` notably keeps the encoding reported by GitHub. Lists are limited to
the first page of 100 items. `issue REPO NUMBER` and `run REPO ID` read a
single item. No write action and no arbitrary API is offered. The token stays
on the Mac during these reads, in the wrapper's memory and the environment of
the child `gh` process. No `gh auth login`, authentication file or `gh`
extension is used.

## Native Git on Kali2

Private repositories require authentication even for `clone` and `fetch`.
On the deployed Kali2, the `credential` sections for the two exact URLs, with
and without `.git`, already enable this helper and `useHttpPath=true`. Native
Git can therefore use them directly. To reproduce this access without changing
a global configuration, restrict the helper to the command concerned:

```sh
git -c credential.helper= \
  -c 'credential.helper=!/home/lolman/.local/bin/openclaw-github credential' \
  -c credential.useHttpPath=true -c http.followRedirects=false \
  clone https://github.com/cluster2600/porscheparts.git
```

For an existing checkout, apply the same options to `fetch`. The helper
accepts only `get` with `protocol=https`, `host=github.com` and one of the
two exact paths, with or without `.git`. `store` and `erase` record nothing.
Before any hand-over, the Mac checks the repository name and ID again.

**Git receives the token in memory on Kali2**, over the encrypted SSH channel
and the private pipe of the credential protocol. Its intrinsic scope remains
that of the GitHub credential; filtering two URLs in this helper does not
reduce the rights of the token itself. Never run the real helper directly in a
terminal or tool output, capture its output in a report, use `tee`, enable
credential tracing or record its result. Automated tests use only a stub with
no secret. The helper does not grant permission to publish or push: every
write remains subject to the requested scope.

## Verification

```sh
python3 -m unittest discover -s tests -p test_openclaw_github_bridge.py -v
```

The tests cover the two identities, the refusal, before authentication, of
other repositories/actions and of traversing paths, the credential protocol,
the refusal of an unexpected GitHub identity and session revocation.
The [evidence on Kali2](../../twins/picogk-station-demo/qualification/runtime/github-access/proof.json)
separately confirms `git ls-remote`, the read of the two private READMEs and a
successful `git push --dry-run` for each repository, without creating any
remote ref. The helper accepts the repeatable `capability[]` and `wwwauth[]`
metadata sent by Git 2.53; they never change the scope of the credential.
