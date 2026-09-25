---
format: 1920x1080
duration: 24s
message: "F38 finally keeps the scan morphology, but the current screens still reject structural simulation, printing and engine start."
arc: Geometry → Operation → Cooling and strength → Industrial verdict
audience: engineers and LPBF manufacturer
mode: autonomous
---

## Frame 1 — Scan-conforming skin

- status: outline
- src: compositions/frames/01-brep.html
- duration: 5s
- transition_in: cut
- poster: 3.0s
- scene: Slow rotation of the reconstructed F38 cylinder head, with the scan envelope in wireframe and three geometric criteria.

Open on the F38 skin derived from the scan. The badges show the minimum thickness, the trapped volume and the support fraction from the F38 report. Blueprint `camera-journey`; rule `multi-phase-camera`.

## Frame 2 — Functional cutaway

- status: outline
- src: compositions/frames/02-cutaway.html
- duration: 7s
- transition_in: cut
- poster: 4.0s
- scene: Animated cutaway view showing four valves, rocker arms, oil galleries and the air path between fins.

Make the cutaway the explanatory core: the four valves move in pairs, the shafts and rocker arms stay visible, oil is coded cyan and external cooling blue. The paths are drawn only on the corresponding geometry. Blueprint `camera-journey`; rules `svg-path-draw` and `multi-phase-camera`.

## Frame 3 — Dual validation

- status: outline
- src: compositions/frames/03-validation.html
- duration: 7s
- transition_in: cut
- poster: 4.2s
- scene: OpenFOAM compared against an analytical correlation, then structure and LPBF manufacturing.

The values come from the F38 reports: heat transfer coefficient, projected temperature and the failure of the structural mesh. The bars compare the two methods without hiding their pressure-drop discrepancy; an inset separates numerical results from the missing physical tests. Blueprint `dataviz-countup`; rules `stat-bars-and-fills` and `svg-path-draw`.

## Frame 4 — Manufacturability decision

- status: outline
- src: compositions/frames/04-verdict.html
- duration: 5s
- transition_in: cut
- poster: 3.0s
- scene: Cylinder head in print orientation with the coupon matrix and a conditional verdict.

End on the part in LPBF orientation, its surfaces to be machined and the number of hot coupons. Clearly show two columns: numerical evidence obtained and physical gates still closed. The last shot never says "engine-validated" as long as the scale and the 917 interfaces are not measured. Rule `stat-bars-and-fills`.
