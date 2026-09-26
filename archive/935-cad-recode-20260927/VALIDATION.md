# Publication verification

Verified on 27 September 2026 before pushing the private research branch:

- `make check`: exit 0 on the current upstream base. Main discovery suite: 3,067 tests, 136 skipped; subsequent targeted suites, catalogue checks, generated pages and strict documentation-link checks also passed.
- Dedicated local CAD-Recode discovery: 13 tests, 4 skipped (CAD/USD dependencies unavailable in this environment). The historical VM CAD and USD checks are described separately in `REPRISE.md`; they are not claimed as rerun here.
- Every archived file listed in `manifest.json` matched its recorded SHA-256. Raw scan formats, raw-scan directories, authentication state and common credential patterns were excluded from the staged package.
- Source/config/test whitespace checks passed. Historical Markdown hard line breaks and the generated USD trailing blank line are preserved to avoid changing archived file hashes.
- 24 OpenClaw execution records, 24 completed replies and web-fetch receipts; eight retries were necessary. Raw model findings remain unapproved. The controlled synthesis is the research conclusion.
- Approved Vast wrapper returned `expired_verified_absent` for the bounded CAD-Recode VM session. No replacement rental was started.

This is an archival/source-code verification, not physical calibration, manufacturing release or structural/thermal validation of the head.
