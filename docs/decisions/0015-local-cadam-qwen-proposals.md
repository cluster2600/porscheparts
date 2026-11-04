# ADR 0015: Local CADAM/Qwen proposals with independent acceptance

Date: 2026-11-04. Status: accepted for the bounded synthetic coupon software branch.

## Context

The owner requested CADAM installation and local Qwen generation without sending
scan data to a service. The existing engineering chain retains PicoGK, editable
STEP/FreeCAD masters, Gmsh, OpenFOAM, CalculiX and Adamantine. CADAM's hosted
account workflow is unsuitable for this local-only requirement.

## Decision

Use a separate local CADAM entry that imports its unmodified viewer, worker,
OpenSCAD WASM compiler and exporter. A same-origin backend calls one fixed
loopback MLX model endpoint. Run both dedicated servers under a nonlocal-outbound
denial policy, with offline model loading and no external fallback. Restrict
browser connectivity by CSP. Send a dimensional specification, not the reference
coupon source or scan, to the model.

Keep an independent immutable contract and verify the actual exported STL.
Compilation alone does not accept a candidate. Preserve prompt, raw response,
source, STL, failures, model/runtime receipts and checksums. Source changes
invalidate previous verification. This is assistance for explicitly specified
coupons and proposals; no engine master or physical release authority changes.

## Evidence and consequences

The [runbook](../architecture/cadam-local-qwen.md) and
[aggregate receipt](../research/cadam-qwen-local-20261104.json) record two identical
accepted generations, 70 checks each, 9 API/negative controls and 8 backend tests.
Initial failures are retained. This scope grants no general reconstruction,
STEP conversion, head simulation or metal build qualification. The model's
upstream revision is unknown; local byte hashes are retained instead. The
existing authenticated LM Studio service and upstream CADAM files are unchanged.
