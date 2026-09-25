---
workflow: general-video
flow: automation
storyboard: no
message: "Show how the four-valve Porsche 917 F38 cylinder head works, cools and is manufactured, with its validation results visible."
destination: desktop-engineering-review
aspect: 1920x1080
language: fr
audience: engineers and LPBF manufacturer
length: 24s
angle: technical demonstration with cutaway view
narration: no
---

## Intent

Short technical film of the F38 checkpoint: scan-conforming exterior view,
kinematic screen of the four valves and rocker arms, recomputation of the air
channel, then the thermal and LPBF verdict. The render must show the measured
failures and must never present the faceted B-Rep as production CAD.

## Assets

- `assets/` — images and sequences computed from the F38 geometry, adopted locally with their provenance.

## Customizations

- Slow rotation of the part, cutaway opening and synchronized animation of the four valves.
- Overlay of the thermal fields, the air/oil flows and the LPBF criteria.

## Notes

- Horizontal 1920×1080 format for engineering review on a desktop.
- Deliberate silence: no music or voice may mask the technical character.
- Every metric stays conditional on the scan scale until a physical reference is available.
- The material qualification, 917 fit and physical test gates stay separate from the virtual validations.
