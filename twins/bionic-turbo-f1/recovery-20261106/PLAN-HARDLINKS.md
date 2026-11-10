# Recovery revision after archive-layout rejection

The first contact-package extraction stopped before creating its payload
directory: two members are TAR hardlinks and `file-manifest.json` is embedded
beside the 28 listed payloads. The initial rule rejected them. Its reconstructed
archive and empty stdout receipt remain in the private `contact-source`
directory; no failure is reclassified as success.

Before a new attempt, extend the exact allowlist with the historical embedded
manifest's pinned SHA-256 and byte size. Logical payload coverage stays 28 and
60 files respectively; the embedded manifest is counted separately.

Accept a hardlink record only if its target is an allowlisted **regular** member
of the same archive and both paths have identical expected sizes and digests.
Materialise the verified target bytes as a new regular file; never create a
filesystem link. Reject symlinks, link chains, cycles, external targets,
mismatched identities and special members. Validate the complete member set
before writing, then independently hash every materialised file. Add positive
and rejection tests before the new real attempt. All other limits and
prohibitions in `PLAN.md` remain unchanged.
