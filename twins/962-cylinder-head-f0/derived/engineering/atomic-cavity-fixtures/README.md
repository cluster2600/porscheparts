# Actual atomic-cavity compile and three synthetic fixtures

Two native synthetic repairs succeeded, and the fixed-vertex case correctly refused without exporting a candidate. Both successful outputs have **9 vertices, 21 edges, 14 faces, Euler characteristic 2 and exact signed volume 3,511,808 mm³**. These are completed fixture results from the actual compiled source002, not a head result.

| Literal fixture | Actual return code | Poor triangles before → after | Actual candidate minimum triangle SICN | Export |
|---|---:|---:|---:|---|
| Two-vertex known collapse | 0 | 2 → 0 | 0.8660254037844386 | 9V / 14F |
| All vertices fixed | 3 | 2 → unmeasured | null | None |
| Four-vertex disk quotient | 0 | 4 → 0 | 0.8660252299093737 | 9V / 14F |

The unchanged necessary triangle threshold is 2/29. This triangle measure is distinct from the tetrahedral SICN ≥ 0.1 gate. A single simultaneous quotient maps a declared connected group to its declared keeper; it does not claim that a sequence of intermediate SMS edge collapses would be admissible.

The two successful complete arrays independently match every frozen coordinate byte in vertex order, every origin byte, and every face row modulo cyclic starting-corner rotation, preserving winding. Independent exact-dyadic checks cover the whole closed edge/vertex manifold, connectedness, absence of duplicates/orphans, fixed coordinates, original exterior faces, affected and original-patch boundary chains, normals and signed volume. Each actual output has four affected surviving faces and eight final affected-neighbor checks, with zero recorded failures. Native envelope guard results are retained observations; the independent reviewers did not replay CGAL.

The all-fixed report was written at input association, before quotient construction or quality evaluation. Its minimum remains null; its default counters are not measurements. Its result directory contains only the rejection report. The input/reference records retain their original preparation-time false authority/result flags; the later actual root and peer reviews form the separate completed-result ledger.

## Evidence and execution scope

- [Exact frozen inputs](inputs/), [complete literal references and reserved six-order quality ranges](references/), [frozen assessor and method](assessment/), and [actual tiny outputs](results/) are included byte-for-byte.
- [Root and independent reviews](reviews/) cover the complete saved arrays and actual execution associations. The independent input-association supplement also reconstructs the original bad-seed incidence plus exact x = ±76 fixed-mask rule for each input.
- [Allowlisted projections](projections.json) retain the original lifecycle, phase and contract values. Compile and fixture phases have complete 15- and 42-entry before/after input hash maps, with unique role labels replacing local preparation locations. The [original inventories](original-records.json) preserve all eight compile artifacts and all 18 fixture artifacts, including the hashes of omitted material.
- [Source bindings](source-bindings.json) identify source002, preserved source001, the unchanged shared include and the executed controller versions. Source002 is linked by its repository path and SHA-256 rather than duplicated. The compile phase used controller snapshot c2191896…; the fixtures used 05390ea8…. A source path alone does not identify an older snapshot.

The one actual compilation returned 0 in 55.9424030832015 s. It produced a 911,232-byte AArch64 executable with SHA-256 `096a6bba7c7103afb4af0b99417a715f66960c7bf972d47136a706b97f020dff`. The executable is omitted. Its [exact compiler log](compile/native.log) contains informational ABI notes, without error or warning diagnostic lines.

The compile limit was 300 s, 4 GiB, two CPUs and a 1 GiB temporary filesystem. Each serial fixture had a 60 s limit, 512 MiB, two CPUs and no temporary filesystem. Swap and networking were disabled and the container root was read-only. All three actual jobs stopped, were reaped and their verified owned containers were removed; no OOM occurred. Their controller wall times were 0.9845275417901576, 0.9307507909834385 and 0.99404316698201 s. These records do not measure peak RSS or actual CPU utilization. No retry occurred.

Commands, host paths, owner/container identifiers, raw lifecycle stdout/stderr, runtime binaries, full upstream headers and head arrays are omitted. Projections are explicitly selected fields, not full original receipts. Original receipt digests and complete inventories bind the retained originals. Exact reference/assessor records preserve their historical repository-relative preparation locators; they are audit snapshots, not a relocated executable workflow.

## Integrity check

From this directory, run:

```sh
python3 verify.py
```

The standard-library checker verifies every payload byte count and SHA-256, regular-file status and complete directory closure against [receipt.json](receipt.json). It does not rerun geometry, native guards or full-array assessments. The exact original assessor is provided for inspection, with its original source and reference bindings.

The preserved [source001 → source002 diff](provenance/source001-to002.diff) adds only fixed connected topology/Euler validation and a requirement for an initially poor mesh followed by zero poor faces with a nonworsening minimum. [Attribution](ATTRIBUTION.md) distinguishes project material from the CGAL scalar-predicate provenance.

This capsule permanently covers the actual compile and three synthetic fixture outcomes only. No head surface, independent global distance/intersection screen, volume mesh, solver, material, thermal, strength, LPBF or manufacturing qualification is established here. No head execution authority follows from this record.
