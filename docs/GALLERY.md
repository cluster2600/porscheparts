# Gallery

The repository's existing figures in one place, grouped by workstream. Every
image below is a computed figure, a CAD render or a diagram. **None is a
photograph of a part, and none is evidence of physical behavior**: each caption
says what the image shows, and the linked page says what it does and does not
prove. Near-duplicates are left out; the `archive/` tree is not shown.

## 964 structure

The torsion model of the 964 body shell, built from a scan and the workshop manual. Explained in [`twins/964-chassis/fea/README.md`](../twins/964-chassis/fea/README.md) and [`twins/964-chassis/README.md`](../twins/964-chassis/README.md).

<table>
<tr>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="media/diagrams/964-hero.gif" alt="The full 964 cell model rotating, colored by von Mises stress under the torsion load" width="100%"></a><br><sub>Full cell under torsion, rendered from a mesh and result snapshot. A computed field, not a measured car. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="media/diagrams/964-modele-coque.svg" alt="The shell model: bare floor pan next to the full cell" width="100%"></a><br><sub>What the shell model contains, from bare floor pan to full cell. A model description, not a test. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="media/diagrams/964-chemin-effort.svg" alt="von Mises stress on the bare floor pan under torsion" width="100%"></a><br><sub>Load path on the bare floor pan: the side rails carry the load. Computed, not measured. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="media/diagrams/964-mecanisme-architecture.svg" alt="Share of shear in stiffness by architecture" width="100%"></a><br><sub>How the stiffness mechanism shifts along the architecture ladder, from the 3,000-case corpora. Numerical, not physical. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="media/diagrams/964-echelle-architectures.svg" alt="Torsional stiffness by architecture in linear and quadratic shells" width="100%"></a><br><sub>The architecture ladder in both element orders, with the per-architecture deviation. A model comparison only. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/964-chassis/README.md"><img src="../twins/964-chassis/evidence/plan_aligned.png" alt="Underside of the 964 scan in the vehicle frame, colored by height above ground" width="100%"></a><br><sub>The scan after symmetry correction, in the vehicle frame. It locates no datum point. <a href="../twins/964-chassis/README.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="../twins/964-chassis/README.md"><img src="../twins/964-chassis/evidence/overlay.png" alt="Manual datum points plotted on the aligned scan" width="100%"></a><br><sub>The datum network placed on the scan, with P21 landing in the rear bumper area. It proves no datum position. <a href="../twins/964-chassis/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/964-chassis/fea/README.md"><img src="../twins/964-chassis/evidence/stress.png" alt="Plan and side views of node stresses under torsion, with the rear cross member detached" width="100%"></a><br><sub>An earlier stress plot kept as evidence; it predates the removal of a cross member that carried nothing. <a href="../twins/964-chassis/fea/README.md">Explained here</a>.</sub></td>
</tr>
</table>

## 993 parts: print screens and renders

Geometric LPBF slicing screens (labels in French) and Omniverse renders of F0/F1 concepts. Each slicing screen shows a real section at every layer and a proxy support envelope; none is a laser toolpath, a machine file or a distortion result, and printing stays prohibited for every part. See [`AM_VALIDATION_PIPELINE.md`](AM_VALIDATION_PIPELINE.md) and the dossiers in [`docs/993/`](993/).

<table>
<tr>
<td width="33%" valign="top"><a href="993/993_EXHAUST_MANIFOLD_IN625_F0.md"><img src="../parts/993-eng-exhaust-manifold-in625-f0-0001/evidence/lpbf-f0/993-eng-exhaust-manifold-in625-f0-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the IN625 exhaust manifold F0" width="100%"></a><br><sub>Exhaust manifold F0, IN625, build_z, 40 µm. Geometry only. <a href="993/993_EXHAUST_MANIFOLD_IN625_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_K16_TURBINE_WHEEL_IN718_F0.md"><img src="../parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/lpbf-f0/993-eng-k16-turbine-wheel-in718-f0-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the IN718 K16 turbine wheel F0" width="100%"></a><br><sub>K16 turbine wheel F0, IN718, roll_y_45. The F0 itself is rejected on its screens. <a href="993/993_K16_TURBINE_WHEEL_IN718_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_INTERCOOLER_BRACKET_TI_F0.md"><img src="../parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/lpbf-f0/993-eng-intercooler-bracket-ti-f0-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the Ti-6Al-4V intercooler bracket F0" width="100%"></a><br><sub>Intercooler bracket F0, Ti-6Al-4V, build_x. Provisional route is CNC. <a href="993/993_INTERCOOLER_BRACKET_TI_F0.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="993/993_TURBO_HEAT_SHIELD_IN625_F0.md"><img src="../parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/lpbf-f0/993-eng-turbo-heat-shield-in625-f0-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the IN625 turbo heat shield F0" width="100%"></a><br><sub>Left turbo heat shield F0, IN625, build_x. Geometry only. <a href="993/993_TURBO_HEAT_SHIELD_IN625_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_DOOR_OPENER_LEVER_ALSI10MG_F0.md"><img src="../twins/993-door-opener-lever-alsi10mg-f0/evidence/lpbf-f0/993-int-door-opener-lever-f0-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the AlSi10Mg door opener lever F0" width="100%"></a><br><sub>Door opener lever F0, roll_y_45, 2,664 layers. No print authorized. <a href="993/993_DOOR_OPENER_LEVER_ALSI10MG_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_SWITCH_TRIM_RING_F1.md"><img src="../twins/993-switch-trim-ring-f1/evidence/lpbf-f1/993-int-switch-trim-ring-f1-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the switch trim ring F1" width="100%"></a><br><sub>Switch trim ring F1 at 50 µm, 580 layers; the ring has since moved to a turned route. <a href="993/993_SWITCH_TRIM_RING_F1.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="993/993_EMBOUT_TITANE_F1.md"><img src="../twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-screen.png" alt="LPBF slicing screen of the titanium exhaust tip F1" width="100%"></a><br><sub>Titanium exhaust tip F1, roll_y_25. Depowdering of the annular channel is not demonstrated. <a href="993/993_EMBOUT_TITANE_F1.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md"><img src="../twins/993-oval-exhaust-tip-in625-f0/evidence/lpbf-f0/oval-tip-lpbf-build-screen.png" alt="The IN625 oval tip placed on a nominal EOS M 290 build plate" width="100%"></a><br><sub>Oval tip on a nominal EOS M 290 plate in roll_y_25. No supports, toolpath or recoater collision. <a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md"><img src="../twins/993-oval-exhaust-tip-in625-f0/evidence/simready-f0/oval-tip-in625-f0-ovrtx.png" alt="OVRTX render of the oval tip SimReady asset" width="100%"></a><br><sub>Isolated SimReady asset of the oval tip. An inspection prop, not a fitted part. <a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md"><img src="../twins/993-oval-exhaust-tip-in625-f0/evidence/simready-f0/grasp-preview-overlay.png" alt="Grasp annotation of the oval tip in four point views" width="100%"></a><br><sub>Grasp annotation reviewed visually; not a gripper validation. <a href="993/993_OVAL_EXHAUST_TIP_IN625_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_PISTON_CP1_COOLING_GALLERY_F0.md"><img src="../twins/993-m64-60-piston-gallery-f0/evidence/lpbf-f0/piston-lpbf-build-screen.png" alt="The CP1 piston F0 tilted on a nominal build plate" width="100%"></a><br><sub>Piston F0 in roll_y_45 on a nominal Sapphire plate. The F0 is rejected on its hot screen. <a href="993/993_PISTON_CP1_COOLING_GALLERY_F0.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="993/993_PISTON_CP1_COOLING_GALLERY_F0.md"><img src="../twins/993-m64-60-piston-gallery-f0/evidence/simready-f0/piston-cp1-gallery-f0-ovrtx.png" alt="OVRTX render of the isolated CP1 piston prop" width="100%"></a><br><sub>Isolated piston prop rendered in OVRTX; the engine interfaces are absent. <a href="993/993_PISTON_CP1_COOLING_GALLERY_F0.md">Explained here</a>.</sub></td>
</tr>
</table>

## M64 cylinder head

The synthetic, non-qualified M64 head twin: CAD sections, mesh-quality counts and valvetrain screens. Each image is explained in its report under [`docs/reports/`](reports/).

<table>
<tr>
<td width="33%" valign="top"><a href="reports/M64_G1_PARAMETRIC_SKELETON_20260914.md"><img src="../twins/m64-cylinder-head/evidence/g1-parametric-20260914/m64-head-skeleton-section-xz.svg" alt="XZ section of the G1 parametric head skeleton" width="100%"></a><br><sub>Placeholder layout of the G1 skeleton, not sourced M64 dimensions. <a href="reports/M64_G1_PARAMETRIC_SKELETON_20260914.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_G2_COMPRESSION_AUDIT_20260924.md"><img src="../twins/m64-cylinder-head/evidence/g2-compression-audit-20260924/head-section.svg" alt="Mid-plane section of the synthetic G2 cylinder head" width="100%"></a><br><sub>G2 head section used for the compression audit; no sealed chamber is proven. <a href="reports/M64_G2_COMPRESSION_AUDIT_20260924.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_G2_SPARK_PLUG_PACKAGING_20260924.md"><img src="../twins/m64-cylinder-head/evidence/g2-spark-plug-packaging-20260924/plug-section.svg" alt="CAD section of the two candidate spark plug envelopes" width="100%"></a><br><sub>Synthetic plug envelopes in section; no physical sealing or supplier fit. <a href="reports/M64_G2_SPARK_PLUG_PACKAGING_20260924.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="reports/M64_G3_SEAT_CONTACT_20260925.md"><img src="../twins/m64-cylinder-head/evidence/g3-seat-contact-20260925/seat-contact-section.svg" alt="Local CAD section of the candidate intake seat" width="100%"></a><br><sub>Candidate intake seat in section; no sealing, contact pressure or manufacturability proven. <a href="reports/M64_G3_SEAT_CONTACT_20260925.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_FOUR_VALVE_DISTRIBUTION_MODULE_20260907.md"><img src="../twins/m64-cylinder-head/evidence/four-valve-design-v2-20260907/four-valve-design-assembly-and-sections.png" alt="STEP of the V2 four-valve sub-assembly with native sections" width="100%"></a><br><sub>V2 sub-assembly from the reimported STEP; no head body, no engine fit. <a href="reports/M64_FOUR_VALVE_DISTRIBUTION_MODULE_20260907.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_V1_VALVETRAIN_20260914.md"><img src="../twins/m64-cylinder-head/evidence/valvetrain-v1/valvetrain-v1-kinematics.png" alt="V1 valvetrain lift, acceleration and piston clearance against crank angle" width="100%"></a><br><sub>V1 lift, acceleration and piston clearance on assumed parameters, not M64 ones (labels in French). <a href="reports/M64_V1_VALVETRAIN_20260914.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="reports/M64_V1_VALVETRAIN_20260914.md"><img src="../twins/m64-cylinder-head/evidence/valvetrain-v1/valvetrain-v1-float-sweep.png" alt="V1 valve float and bounce against engine speed, intake and exhaust" width="100%"></a><br><sub>One-degree-of-freedom float sweep against speed; a model trend, not a rig result. <a href="reports/M64_V1_VALVETRAIN_20260914.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_THERMAL_FACE_PROPOSALS.md"><img src="../twins/m64-cylinder-head/evidence/thermal-face-proposals-and-section.png" alt="Candidate thermal face groups and a section of the F53 reference" width="100%"></a><br><sub>Candidate face groups on the scan-derived reference; a proposal, not a thermal result. <a href="reports/M64_THERMAL_FACE_PROPOSALS.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_SURFACE_METHOD_COMPARISON_20260909.md"><img src="M64_SURFACE_METHOD_COMPARISON_20260909.png" alt="Mesh quality indicators of two surface methods on native face 37" width="100%"></a><br><sub>Mesh indicators of two trials; nothing about engine performance. <a href="reports/M64_SURFACE_METHOD_COMPARISON_20260909.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="reports/M64_HYBRID_PAIR_CORRECTION_20260909.md"><img src="images/m64-hybrid-pair-quality-20260909.png" alt="Native checkMesh defect counts before and after the unions" width="100%"></a><br><sub>Mesh defect counts only, not a physical field or an accepted mesh. <a href="reports/M64_HYBRID_PAIR_CORRECTION_20260909.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_F58_CORRECTED_COUPON_20260908.md"><img src="../twins/m64-cylinder-head/evidence/corrected-coupon-diagnostic-20260908.png" alt="Corrected coupon against the thermal-only reference" width="100%"></a><br><sub>Computed coupon values over a common window; not melt-pool measurements. <a href="reports/M64_F58_CORRECTED_COUPON_20260908.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_LOCAL_BERNSTEIN_REPAIR_20260907.md"><img src="../twins/m64-cylinder-head/evidence/935-reference-bernstein-local-repair-before-after.png" alt="CAD and before/after section of the local Bernstein repair" width="100%"></a><br><sub>Before/after section of a local surface repair; a diagnostic, not a released geometry. <a href="reports/M64_LOCAL_BERNSTEIN_REPAIR_20260907.md">Explained here</a>.</sub></td>
</tr>
</table>

## Digital twin and pipeline diagrams

Logical diagrams of the twin state and of the M64 execution chain. Some labels are in French. They show planned or recorded relationships, not results.

<table>
<tr>
<td width="33%" valign="top"><a href="DIGITAL_TWIN.md"><img src="media/diagrams/digital-twin-993-etat.svg" alt="Register of the sourced 993 twin state" width="100%"></a><br><sub>Sourced twin state as a register: wheel sets and known interfaces; brakes not admitted, 3D positions unknown. <a href="DIGITAL_TWIN.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_MULTIPHYSICS_EXECUTION.md"><img src="media/diagrams/m64-stack.svg" alt="M64 multiphysics software stack, from scan to OpenUSD" width="100%"></a><br><sub>The planned tool chain from scan to OpenUSD; a plan, not an executed validation. <a href="reports/M64_MULTIPHYSICS_EXECUTION.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_MULTIPHYSICS_EXECUTION.md"><img src="media/diagrams/m64-validation.svg" alt="Ten-step M64 validation sequence with review loops" width="100%"></a><br><sub>The validation gates in order, with their loops back to CAD; no gate is shown as passed. <a href="reports/M64_MULTIPHYSICS_EXECUTION.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="reports/M64_PICOGK_EXECUTION.md"><img src="media/diagrams/m64-vast-run.svg" alt="Bounded remote compute run, from pinned image to instance deletion" width="100%"></a><br><sub>How a rented compute run is bounded and cleaned up; a procedure, not a result. <a href="reports/M64_PICOGK_EXECUTION.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="reports/M64_700CH_ENGINE_RESEARCH.md"><img src="media/diagrams/m64-700ps-execution.svg" alt="Execution chain of the 700 PS research target" width="100%"></a><br><sub>The research chain for the 700 PS target, ending on a question: are the criteria proven on the same product? Nothing in it is demonstrated. <a href="reports/M64_700CH_ENGINE_RESEARCH.md">Explained here</a>.</sub></td>
</tr>
</table>

## 917 line (archived)

**Archived line.** The 917 work is retired as a product and kept as a numerical regression; see [`ARCHIVE.md`](../ARCHIVE.md) and [`twins/reference-917-engine/README.md`](../twins/reference-917-engine/README.md). Metal printing and engine start remain prohibited. Labels are in French.

<table>
<tr>
<td width="33%" valign="top"><a href="../twins/reference-917-engine/README.md"><img src="../twins/reference-917-engine/evidence/f29/figures/cad-comparison-2v-4v.png" alt="F29 conceptual cylinder heads, 2V and 4V, as four CAD previews" width="100%"></a><br><sub>F29 clean-sheet solids reopened in OCCT; a CAD preview, not a CFD, FEA or Omniverse result. <a href="../twins/reference-917-engine/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/reference-917-engine/README.md"><img src="../twins/reference-917-engine/evidence/f31/figures/reference-fea-2v-4v.png" alt="F31 FE screening of the 2V/4V architectures" width="100%"></a><br><sub>Uncorrelated CalculiX results on a defeatured deck; a comparison under one model only. <a href="../twins/reference-917-engine/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/reference-917-engine/evidence/f39-functional-video/README.md"><img src="../twins/reference-917-engine/evidence/f39-functional-video/917-head-f39-how-it-works-poster.png" alt="Poster frame of the F39 how-it-works video: four-valve section at closure" width="100%"></a><br><sub>An explanatory frame reusing F37 kinematics with an unmeasured cam profile; not a dynamic validation. <a href="../twins/reference-917-engine/evidence/f39-functional-video/README.md">Explained here</a>.</sub></td>
</tr>
<tr>
<td width="33%" valign="top"><a href="../twins/reference-917-engine/README.md"><img src="../twins/reference-917-engine/evidence/f42-omniverse-validation/917-head-f41-welded-ovrtx-preview.png" alt="OVRTX render of the welded F41 cylinder-head mesh" width="100%"></a><br><sub>Shows that the USD opens and renders with a closed topology; not a photograph of a part. <a href="../twins/reference-917-engine/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../twins/reference-917-engine/evidence/f49-solid/README.md"><img src="../twins/reference-917-engine/evidence/f49-solid/917-head-f49-2v-4v-sections.png" alt="F49 half-sections of the 2V and 4V candidates with gas and oil cores" width="100%"></a><br><sub>Candidate sections whose STEP files were rejected; not a proof of manufacture. <a href="../twins/reference-917-engine/evidence/f49-solid/README.md">Explained here</a>.</sub></td>
<td width="33%" valign="top"><a href="../README.md"><img src="../twins/reference-917-engine/evidence/f50-additive-print/media/917-head-f50-lpbf-process-dashboard.png" alt="F50 virtual LPBF process dashboard: sections per layer, unsupported area and AdditiveFOAM coupon results" width="100%"></a><br><sub>Virtual process screening; neither engine operation nor physical validation. <a href="../README.md">Explained here</a>.</sub></td>
</tr>
</table>

---

*43 images. Adding one: link an existing file only, with a caption that says what it shows and what it does not prove (see [`TRANSLATION.md`](TRANSLATION.md), "Diagrams and images").*
