# Real local SSH authentication — September 7, 2026

**Result: passed**, on Kali x86 in the exact parent image already present:
`ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126`.
The embedded sshd wrapper has the same SHA256 as the repository script.

Unlike the earlier `sshd -T` test, this one actually starts sshd and makes SSH
connections in BatchMode with strict host key checking. Two **synthetic and
ephemeral** key pairs are generated in the container; no user key, no OpenBao
or Keychain secret is used. The usual SSH transport to Kali remains outside
the test.

## Checks obtained

- Without `authorized_keys`, the key is refused.
- After injecting the file as root:root/0600 and the directory as 0700,
  **the same key succeeds, without restarting sshd**.
- Another identity is refused.
- Switching `authorized_keys` to 0666 leads to a refusal, with a server
  diagnostic of incorrect permissions.
- The chown/chmod operations equivalent to the SSH block of the onstart restore
  authentication; the full onstart and its GPU services are not launched.
- A wrong host key in the known-hosts file is refused.

The mechanism of a transient refusal before injection/permission correction is
therefore **reproduced locally**. This does not prove that this mechanism
occurred on Vast, nor the real order of its launcher, nor the behavior of its
proxy. The full local-ai image is not run here: its SSH parent is tested. No
production script was modified.

## Fixes to study, not applied

1. Prepare the permissions of `.ssh` and of the injected key before the
   listener opens, when the launcher order allows it.
2. Handle the `sshd -T` / `-t` modes explicitly: the onstart already invokes
   `sshd -T` before its permissions block. Naively adding a wait for the key to
   every invocation of the wrapper could introduce a circular deadlock.
3. Provide a short bounded wait for the injected file in the onstart, without
   fabricating a key or replacing the expected identity.
4. Examine a strictly bounded initial authentication grace period, keeping the
   identity, the host key checks and the total timeout.

These avenues must be tested in isolation and tied to observations of Vast's
real order before concluding on the cause or modifying production.

## Reproduction, only in a disposable container

Never run the script directly on a workstation. It creates a synthetic
`/root/.ssh/authorized_keys` file in the disposable container.

From a copy of the repository on an x86 Docker host:

```sh
timeout 90 docker run --rm -i --network none --cpus 1 --memory 1g \
  --pids-limit 64 --tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m \
  --entrypoint /usr/bin/python3 \
  ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126 \
  - < tests/manual/simready_ssh_auth_smoke.py
```

The listener is exclusively `127.0.0.1:22222` in the container without
network; no LAN/public port is published. The process and the temporary keys
were deleted; the Docker inventory filtered on the image is empty after the
test. The receipt is in
`twins/m64-cylinder-head/evidence/ssh-auth-smoke-20260907.json`.
