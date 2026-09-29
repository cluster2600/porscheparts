# m64-charge-air-0001 — status

**Concept geometry (F1), compiled once in container — no dimensions validated.**

- Sources: `source/{ChargeAirGeometry.cs, ChargeAirParameters.cs, Program.cs}` (parametric PicoGK C#; every dimension tagged `ASSUMPTION` in `provenance.json` — vendor envelopes are packaging bounds, not OEM interface dims).
- Build: container build log in `validation/docker-build-attempt.log` ends **0 Warning(s), 0 Error(s)** against the pinned picogk-m64 image; run attempt in `validation/docker-run-attempt.log`. Host dotnet 6 cannot target net9 (provenance `build_state`).
- PET nomenclature landed after this lane (deck branch): charge-air identities now PET-sourced in `catalog/parts/993-ca-*-pet-0001.json`; see `docs/research/pet-107-transcription-2026-09-29.md`. Dimensions still open.
- Gates before promotion: OEM interface dimensions, hose routing vs engine envelope, charge-air temperature service check. No print decision yet (ranking proposal in the lane report).
