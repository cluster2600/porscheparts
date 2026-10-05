# ADR 0012 — Local engineering compute, GPU last, measured local AI

## Status

Accepted for implementation on 2026-09-30 by the project owner. The follow-up
prioritizes documentation and local Qwen training before further deployment.

## Decision

1. Apply tailored TOGAF governance, ArchiMate viewpoints and UML behavior/data
   views, rendered in Mermaid. See the [architecture](../architecture/README.md).
2. Author all new material in English and follow the existing immutable-evidence
   translation policy. Include comments, training prompts and generated reports.
3. Retain the existing M64 program and part catalogue. New geometry uses
   PicoGK; existing CAD masters remain authoritative. Reuse the qualified Linux
   station, portable runtime and collector; do not mix older .NET 8 notes with
   the .NET 9 station runtime.
4. Prepare geometry, OpenFOAM/CalculiX calculations, manufacturing studies and
   USD locally on Mac/kali1/kali2. Rent Vast only for a prepared final Omniverse
   review, with explicit budget and teardown verification.
5. Implement a Mac MLX QLoRA pilot after documenting the architecture. Use a
   pinned 4-bit Qwen2.5-Coder-1.5B model due to limited free disk, with 7B as a
   later benchmark. The owner's request authorizes this local pilot, not a
   paid rental or model publication.
6. Train only on newly authored synthetic project-workflow examples with
   declared provenance and disjoint part families. Record actual before/after
   results and keep the base if the adapter does not improve the acceptance
   criteria. Neither model is an engineering authority.

## Consequences

No new scheduler, database, hosted model endpoint or GPU training infrastructure
is introduced. Existing engineering and physical qualification gates remain.
The first training run tests a small workflow-adaptation hypothesis, not general
PicoGK mastery, engine accuracy, manufacturing readiness or material performance.
