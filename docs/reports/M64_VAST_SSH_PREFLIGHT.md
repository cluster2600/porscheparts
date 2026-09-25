# Vast SSH preflight — September 7, 2026

The `deploy/openbao/openbao-vastai` wrapper now separates three proofs:

1. **Usable local key pair**, before registration and paid creation: the
   metadata of the approved private file is validated, then OpenSSH
   `ssh-keygen -y` derives its only public identity. The comparison ignores
   comments. The operation is bounded to 10 seconds, with no input, agent or
   inherited authentication variable. Neither the private key, nor the public
   output, nor the raw error of this command is displayed.
2. **Key listed for the exact instance**: its SSH endpoint is read, the only
   approved key is attached if absent, a strict `true` acknowledgement is
   required, then it is read back (three attempts at most). A POST attachment
   is never replayed automatically. A fixed JSON receipt keeps the ID, the
   unique label and the proof booleans, without keys or comments.
3. **Effective authentication and service**: the SSH BatchMode check and the
   READY marker remain mandatory. The proof from steps 1 and 2 **does not
   prove** that `authorized_keys` was injected into the container.

On a terminal SSH failure, the receipt keeps the host/port actually used, the
return code and derived flags (`permission_denied`, `key_load_failed`,
`bad_key_permissions`). No raw stdout/stderr is logged. Deletion with proof of
absence remains mandatory on failure after creation; these diagnostics disable
no host key, identity or availability check.

The tests use synthetic keys and responses. They prove neither a real
connection on Vast nor a computation on the cylinder head.

The read-only command `ssh-endpoints <id>` exposes separately the
`ssh_host` / `ssh_port` pair and the `public_ipaddr` / `ports[22/tcp][0].HostPort`
pair. It refuses a different returned ID and masks an incomplete or invalid
pair. It does not change the wrapper's current choice, does not attempt a
connection and does not present this metadata as proof of reachability.

The existing selector also normalizes the direct `HostPort` to an integer: Vast
may return it as a decimal string. Non-decimal formats, booleans and values
outside 1 to 65535 are refused. The priority of the complete proxy pair is
unchanged; no proxy address is combined with the direct port, and no
authentication check is relaxed.

Provider references:
[SSH](https://docs.vast.ai/guides/instances/connect/ssh),
[SSH attachment](https://docs.vast.ai/api-reference/instances/attach-ssh-key).
