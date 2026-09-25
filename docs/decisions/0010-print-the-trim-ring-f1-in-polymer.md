# 0010 — The F1 trim ring is published as a printable part, in polymer

Date: 2026-09-25

## Context

[Decision 0009](0009-first-fit-test-print-switch-blank.md) published a fit-test
kit, a measurement instrument. The project owner asked for more: a **part the
repository created**, printable as such.

Of the designed parts, `993-INT-SWITCH-TRIM-RING-F1-0001` is the most complete
and the only `non_critical` one with a real master: a parametric F1 design
whose four main dimensions come from a supplier sheet, taken through the whole
CAD, LPBF-screening and route chain. [Decision 0006](0006-bague-tournee-6063-t6.md)
chose turned 6063 T6 as its manufacturing route.

## Decision

Publish the F1 master, **unchanged**, as a printable polymer part in
`parts/993-int-switch-trim-ring-f1-0001/print/`: a fine STL, a PrusaSlicer 3MF
project and instructions. The design prints front face down with no supports,
in 17 minutes.

- The reference route stays turned 6063 T6 (decision 0006). The polymer print
  is a second route for the same design, not a replacement.
- The record stays at `concept`: the dashboard opening and fit condition are
  unmeasured, and the inner cone is an F1 hypothesis.
- Like 0009, this covers this non-critical part only.

## Consequences

The repository has one part of its own design that anyone can print today, with
its provenance (master file and SHA-256) and its open hypotheses listed next to
the file.
