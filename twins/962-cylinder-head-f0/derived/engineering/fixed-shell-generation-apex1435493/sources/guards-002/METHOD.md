# Runner-guard binding correction

The original prep001 and its held contract remain unchanged. Root passed its
six shell guards, then the original runner guards refused during module import:
the selected sibling runner was 4963f5c6…, while SOURCE_SHA still named the old
9733e94c… cube runner. No mocked method ran in that failed invocation. The
original failure log is preserved and exactly identified in `successor.json`.

This test-only successor changes exactly two assignment lines: SOURCE now
explicitly selects prep001/run_readback.py, and SOURCE_SHA selects its actual
4963f5c6… bytes. Reversing those two lines recovers the original test byte-for-byte.
All 14 test methods and every other function AST are unchanged. The existing
worker, controller, source metadata, resource limits and scientific gates are
unchanged; no nine-file preparation copy was created. The inherited diagnostic
string mentioning the generation cube remains historical source text.

Only stdlib source parsing and byte comparison were performed here. No test,
prepared function, scientific import, native operation or geometry query ran.
Root must run this selected guard source separately and bind its exact identity
and result directly into a future actual child. This correction grants no
generation, stitching, head or physical authority.
