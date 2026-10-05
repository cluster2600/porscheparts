# Integrating research

[Research](README.md) · [English preliminary-ledger view](PRELIMINARY_LEDGER.md) · [Archived French source record](dossier.json)

1. Add a source with a stable ID, publisher/author, direct URL, language,
   edition/date and access status. Distinguish direct reading, excerpts,
   abstracts, copies and search results. Give PDF and printed page numbers,
   figure or post/date. Do not store personal purchase evidence.
2. Link republications to their origin with `origin_source_id`. Record limits
   on independence and keep `independent_of_project=false` for project outputs,
   PorscheFanatics and their derivatives. Copies are not new confirmations.
3. Record each proposition as a `claim` with variant and scope. An absent
   source leaves a research question; an inaccessible source retains an
   unverified-reading status. A photograph or trade name does not establish
   935/993 equivalence.
4. Record numerical parameters with units, variant, conditions, locator and
   uncertainty. Use `null` for unknowns. Distinguish impeller outside diameter,
   fan housing diameter and radial clearance; crankshaft, impeller and
   alternator speeds; static/total pressure and volume/mass flow. Derived
   values retain their formula and inputs in `conditions`.
5. Open a contradiction referencing the affected records. Document a resolution
   with evidence without deleting the original value. Separate variants and
   installations before assuming a source error.
6. Record languages actually read, queries and dates, sites/forums, retained
   and rejected pages, and access blockers. A completed bounded search does
   not establish exhaustive web coverage.
7. Update the synthesis, run checks and publish on the dedicated PR branch.
   Keep geometry sources and scans private until their reuse/publication
   license is established. Preserve original research texts and their hashes;
   label translated reading views separately from immutable source archives.

`engineering_validation` and `engineering_use_approved` remain false in this
ledger. Documented OEM data may be proposed as study inputs, but accepting a
functional model still requires the [validation-plan evidence](../VALIDATION_PLAN.md),
measured interfaces and engineering review. Catalog changes are handled
separately with that evidence; a literature synthesis does not release a part.
