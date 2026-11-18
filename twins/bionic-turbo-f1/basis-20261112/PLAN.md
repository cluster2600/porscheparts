# Interface ledger and comparison basis — method fixed before application

Issue #396, gate `G03-measured-interfaces-and-basis`. This plan prescribes
what is done, what counts as acceptance and what is refused. It is committed
in the same change as the work it governs, so its authority does not rest on
a timestamp: every criterion below is enforced by `basis.py check` and by
`tests/test_bionic_turbo_basis.py`. The receipts were recorded after it. The
retrieval cases were tried once against the corpus while being drafted; none
was changed or removed afterwards.

## Prerequisites

Confirm #394 and #395 at gate level, not at issue level: the unchanged
`baseline-20261106/baseline.py` must validate the recovery ledger and accept
the recorded attestations of `G01-baseline-frozen`, `G01-execution-contract`
and `G02-evidence-recoverable`. If any is refused, stop and report it.

## Scope and resource limits

- Documentary work only: hashing committed files, one in-memory-sized SQLite
  FTS5 index built in a private temporary directory, JSON validation.
- No mesher, solver, OpenFOAM, CloudCompare, Docker container, SSH session or
  remote host. No download and no web request. No paid compute.
- Wall time under one minute per check on the WSL host; no file over 1 MiB;
  no mesh, field or solver byte in Git.
- Nothing under `evidence/**` and no earlier revision directory is edited.
  The recurring turbo automation stays paused. Case 084, the PR229
  `blockMeshDict` and the PR238–256 traversals are not touched.

## Method

1. **Allowlist.** List the committed files that may serve as turbo sources,
   each pinned by SHA-256 with its rights, a variant identity and the units
   its spans carry. Select exact spans: verbatim lines, or one JSON node.
   Exclude by rule the carrier corpus and every other part's documents.
2. **Corpus.** Derive the documentary snapshot from the allowlist alone, with
   the unchanged `benchmarks/free-tools/knowledge.py`. Labelled synthetic
   conflict and hostile fixtures are the only rows without a file span.
3. **Retrieval.** Freeze 30 cases in the composition the unchanged evaluator
   requires (10 reference, 10 unknown, 5 conflict, 5 hostile) and a list of
   known citations written from the cited files, not from the corpus.
4. **Ledger.** One entry per interface or operating condition named by the
   issue: rotor and stator, nut, ports, MRF interface, clearances, shaft
   speed, pressure and temperature boundary conditions, reference geometry.
5. **Conventions.** Define the quantities and their signs, and one declared
   pair of reference conditions for corrected flow and speed.
6. **Gate.** Record a new ledger revision in which only G03 changes, and ask
   the unchanged evaluator for its verdict.

CloudCompare is used only if an authorised turbo surface is available in the
worktree **and** the runtime matrix pins the image identity. Qwen is not used.

## Acceptance criteria

- Every corpus row except a labelled control equals the span read back from
  its pinned file; a moved span or changed file fails the check.
- The unchanged 30-case evaluation passes, with all ten reference cases, and
  **every** known citation is retrieved with its exact phrase, locator,
  variant identity, evidence status and units.
- Every unknown case resolves to a document that says the value is unknown
  or null; no corpus status means "measured".
- Every ledger entry is either measured — an admitted measurement record,
  instrument, method, datum, specimen, licence, repeats, a numeric
  uncertainty and an independent review — or bound to a named missing-data
  gate. Every study value carries its file, span and a literal found in that
  span, and one of the labels `assumed`, `model_derived`,
  `numerical_construct`.
- A published value for another variant is context only and is never marked
  transferable.
- The corrected-flow function reproduces the 20 illustrative points of the
  2026-10-02 research register, which were computed independently of it.
- Only G03 differs from the parent ledger; the opening rule, the comparison
  contract and every other gate are inherited byte for byte in content.

## What is refused

- A dimension, clearance, speed, pressure, temperature or map point with no
  source in the repository stays `null`. Nothing is estimated to fill a gap.
- A value that exists only as a study assumption is recorded as assumed.
- G03 is not marked `engineering_passed` unless the unchanged evaluator
  accepts it. With open blockers it cannot; the honest state is then
  `investigated`, and the gates that depend on it stay closed.
- Missing measurements are listed as requests an outside contributor could
  answer under decision 0019, never as tasks for the owner, purchases or
  commissioned measurement.

## Failure handling

A failed check is kept and reported; no threshold is relaxed and no case is
removed to make the evaluation pass.
