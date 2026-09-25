---
workflow: general-video
flow: automation
storyboard: no
message: "Show the operating principle of the four-valve Porsche 917 F39 cylinder head, its air/oil cooling and the exact limits of its numerical validation."
destination: desktop-engineering-review
aspect: 1920x1080
language: fr
audience: mechanical engineers and LPBF manufacturer
length: 26s
angle: technical cutaway animation
narration: no
---

## Intent

Short technical video showing the F39 analytical envelope derived from the scan
alone, the motion screen of the four valves, the intake/closed/exhaust phases,
then heat removal by local oil and forced air between the fins. The figures on
screen come from the F39 reports.

## Assets

- `assets/f39-exterior.png` — render of the F39 analytical B-Rep.
- `assets/f39-section.png` — cutaway view of the reconstructed volume.
- `assets/f39-cutaway-*.png` — analytical kinematic screens reused from F38.
- `assets/f39-cooling.png` — F39 thermal optimization.
- `assets/f39-lpbf.png` — manufacturability audit of the F39 scan.

## Customizations

- Visual cycle intake → closed/thermal load → exhaust.
- Synchronized motion of the two intake valves, then the two exhaust valves.
- Forced air animated in blue, local oil transfer in green and thermal load in orange.

## Notes

- Deliberate silence for a technical review.
- The lift shown is a 12 mm geometric screen; the real cam profile is not measured.
- The F39 methods are pre-screening models, not a full CHT nor a bench correlation.
- The video grants no authorization for metal printing or engine start.
