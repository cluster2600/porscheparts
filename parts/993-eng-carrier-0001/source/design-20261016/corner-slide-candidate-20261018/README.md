# Editable 24af corner-slide candidate

This bundle rebuilds the declared `first-window-root-corner-slide-v1` geometry from its actual editable construction sources and nominal parameters. The original native candidate is `24af058467fd82a9f0c1d391bf947d427dffd311371cf8f73dafa492d204f4fd`, with an observed CAD mass of **1.2759916739532025 kg** at the retained density. This newly rebased source replay is prepared for review; it has **not run yet**.

`candidate-native.brep` is the native master. `candidate-default.step` is its separately checked default STEP exchange. `candidate-surface.stl` is the dedicated surface export; the builder also emits construction STEP/STL files with separate roles. Geometry generation is independent of the solver and AM toolchains.

## Rebuild into a fresh directory

Use the existing Python 3.10 CAD runtime. `dependencies/runtime.json` lists every pinned runtime file and its original root. No installation or runtime binary is supplied. The bundle can move to another directory; an alternate runtime root must contain the same recorded bytes. Matching package version strings alone do not satisfy this exact replay contract.

```sh
BUNDLE=/absolute/path/to/this/bundle
RUNTIME_ROOT=/absolute/path/to/work/part-workflow/runtimes
PY="$RUNTIME_ROOT/design-standalone/bin/python"
OUTPUT=/absolute/existing/parent/new-24af-replay
"$PY" -I -B "$BUNDLE/rebuild.py" verify --output "$OUTPUT" --runtime-root "$RUNTIME_ROOT"
env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 /usr/bin/nice -n 10 "$PY" -I -B "$BUNDLE/rebuild.py" rebuild --output "$OUTPUT" --runtime-root "$RUNTIME_ROOT"
```

The native child requires absolute nice level 10, one OCCT pool thread and no Python workers. Start the command from a normal nice-0 shell. Its original internal limits are 560 seconds and CPU 520/540 seconds. The reviewed agent execution additionally uses the unchanged owned-process supervisor with a 600-second total budget and 10 + 10 seconds cleanup. A failed attempt retains its raw outputs and assessment; it does not retry or change tolerances.

The output must be absent, outside the bundle, with an existing parent and no symbolic path components. `verify` hashes inputs and installed runtime files without importing CAD. Native generation executes exactly this order:

1. `generator/build_stock.py` calls the actual private `corrected_cad.py` and `normal-builder/cad.py`, using supplied nominal settings and the original contract's five dependencies. It saves raw bodies before its original validity/export/volume gates.
2. The original `import_brep(regenerated-stock/native-body.brep)` then `export_brep(..., candidate-native.brep)` canonicalization runs once. The generated-body hash is expected to be `2fea38f62671bdbe15fc54970c75566e541603d07e8768ea6d0c0b04af0e700e`; its canonical output is expected to be the 24af master above.
3. The original five fresh strict native differences run: baseline minus candidate, d64 minus candidate, candidate minus d64, R1 minus candidate, and candidate minus R1. They use non-destructive, serial, fuzzy-zero Cuts. Raw BREP/null records and complete summaries are saved before gates. Baseline and d64 retention are required; R1 differences describe the distinct design and do not require whole R1 retention.
4. The four original tool columns use fresh candidate imports and strict native Commons. Their raw results and complete boundary records precede the original empty-or-pad-contact predicates. Exact original bounds and the **1.30 kg** ceiling remain.
5. Fresh topology, adaptive measurements, both BREP hashes, all twelve window ledger rows and all four degree-6 rail rows must match the supplied original evidence. A mismatch is recorded and refused without an equivalence fallback.

Read `assessment.json`, `fresh-reproduction-comparisons.json`, `fresh-native-body.json`, `local-measurements-before-gates.json`, all five difference summaries and `four-Common-predicates.json` in the new output. Full protected-roster and surface/STEP records in `evidence/` describe the original 24af only; this command does not rerun those downstream stages. No mechanics or AM replay is included.

## Edit the declared design

The nominal settings are in `payload/parts/993-eng-carrier-0001/source/design-20261016/bounded-webs.json` and `bounded-webs-plan.json`. The two first-window corner shifts are explicit in `generator/normal-builder/cad.py`: only the main scale-0.9 first window moves its scaled A corner by `(1.5, 15/136) mm`, with its true X counterpart. The other ten window branches and four degree-6 C2 rib rails retain their actual source bodies. R1 fillets are not inherited.

For a deliberate new design, edit a separate copy. The exact replay manifest and expected-byte comparisons will then refuse its old 24af identity; new geometry needs its own measurements and downstream results. The original body is 236 faces, 725 edges, 482 vertices, one valid Solid, one shell and zero degenerated edges. These are comparison targets, not invented counts for an edited model.

`generator/build_stock.py` and the private correction each have one declared SOURCE-path rebase. The unchanged normal builder's `from corrected_cad import precise_volume` resolves the supplied **original** correction helper in `payload/.../correction-20261013/`, while the private construction correction is loaded under a distinct module name. `generator/source-changes.json` records whole source inverses and exact helper extractions. `original-source/records.py` preserves the historical design-selection provenance; replay does not recursively execute old observers or load cases.

All coordinates are millimetres in the original source frame, with no pose or scaling added by this bundle. Nominal interface assumptions remain in the supplied interface-study contract. Current nominal-interface drawings and the numerical checkpoint are maintained in the repository at `docs/media/carrier-nominal-interfaces-20261018/` and `docs/reports/carrier-rib-20261018/`. Source origins, licenses and SHA-256 values are in `source-origins.json` and `manifest.json`. Repository material retains the supplied proprietary license; third-party CAD runtime packages retain their own licenses.
