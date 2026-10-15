# Validation and limits

English re-execution of the 2026-10-13 French package (release `bionic-turbo-internal-contact-obligations-2026-10-13`), which stays unchanged as the historical record. The four programs are byte-identical to that package. The 19 parent archives were downloaded from their published releases; each matched the `archive_sha256` committed in its `archive-receipt.json` before extraction. `audit_inputs.py` then verified the 19 manifests against Git commit 050b28b932aee9eaafe4b07e43fad17a6f6ee157 and all 520 payload entries. `input-inventory.json` lists the same manifests and inputs as the French package; only its creation time differs.

Primary exit code 0 in 15.471822 s; independent reader exit code 0 in 12.467482 s, with CPython 3.12.3 on Linux x86-64 (WSL2). The new incidence predicates, all oriented tetrahedra and their cells, and all subcomplex intersections agree. No old polynomial or geometric traversal was recomputed. The 19 manifests and 520 inherited entries are anchored at the Git base; the documents, programs and references frozen before application are unchanged.

The counts are identical to the 2026-10-13 run: 6144 cells, 119808 tetrahedra, 230656 two-incidence and 17920 single-incidence triangles, 82560 cell pairs with a common subcomplex (13696, 34048 and 34816 of maximal dimension two, one and zero). `abstract-tetrahedra.jsonl.gz` and `contacts.jsonl.gz` decompress to the same bytes as the 2026-10-13 files; their gzip digests differ because the gzip header records the write time.

Six references per program before application: two correctly joined tetrahedra, duplicate rejected, inconsistent orientation rejected, multiplicity three rejected, consistent triangulated square and inverted edge rejected. No refusal or correction during the application to the turbo. The general tests started after both readers. These durations are not CFD benchmarks.

Ran 82 tests in 13.973s
OK (skipped=4)
Ran 3954 tests in 233.469s
OK (skipped=223)

`make check` exits with code 0 here, with numpy 2.2.6, matplotlib 3.10.8 and scipy 1.17.1 as in CI. The PR254 log carries six ERROR/FAIL labels outside the turbo; this run carries none, so `test-comparison.json` records `same_labels: false`. The 2026-10-13 run reported 109 turbo tests in its own environment; the difference with 82 is not investigated here.

The written proof uses the local multiplicity of positive chains to pass from the interiors to the lower-dimensional strata. The independent check covers its finite hypotheses and their join to the inherited certificates; it is not an automatic prover of the proof. The Lipman reference sheds light on simplicial inversion, but its manifold hypothesis is not deduced from Euler or from incidence counting alone.

Conclusion limited to the shared PR241 realization on the closed hull of the 153 boxes. Neither equality of the first moments/centers, nor transfer to another native triangulation. The two undecided determinants remain present. The writePrecision 16 conversions, the floating-point accumulations, the configuration and the binary remain open. No candidate, native, solver, CFD, flow rate, power or calibration. Docker and the source volume are preserved; no 084 case replayed.
