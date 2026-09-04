.PHONY: check validate test twin twin-validate engine-contracts engine-components engine-contracts-check 917-complete-parts 917-complete-assembly 917-kinematics-f2 917-detail-f3 917-systems-f4 917-virtual-test-bench 917-test-bench-usd 917-start-support-f5 917-oil-prime-f6 917-motion-video-stages-f7 917-motion-video-render-f7 917-interfaces-f8-check 917-interfaces-f8-preflight 917-performance-envelope-f9 917-variant-geometry-f10-check 917-variant-geometry-f10 917-reengineering-f11 917-clean-sheet-head-f29 917-clean-sheet-head-f29-check 917-clean-sheet-head-f29-figures 917-head-reference-cae-f31-image 917-head-reference-cae-f31 917-head-reference-cae-f31-publish 917-clean-sheet-2026-f32 917-clean-sheet-2026-f32-check 917-cycle-thermal-f33 917-cycle-thermal-f33-check 917-cycle-thermal-f33-test 917-air-oil-controls-f34a-check 917-air-oil-controls-f34a-test 917-doe-f34 917-doe-f34-check 917-doe-f34-test 917-air-oil-seeds-f34b 917-air-oil-seeds-f34b-check 917-air-oil-cycle-f34b-preflight 917-air-oil-cycle-f34b-test 917-air-oil-cycle-f34b-image-test 917-air-oil-cycle-f34b-lock-check 917-air-oil-cycle-f34b-image 917-air-oil-cycle-f34b-smoke 917-integrated-virtual-f33-image 917-integrated-virtual-f33 917-integrated-virtual-f33-publish 917-aircooled-4v-f34-cae-image 917-aircooled-4v-f34-fluidx3d-image 917-aircooled-4v-f34-check 917-aircooled-4v-f34-publish valve-variants omniverse-assembly turbo-cold-side turbo-cold-side-check turbo-variants turbo-variants-check turbo-dyno turbo-dyno-check container-recon container-cadsim container-mesh-cfd container-physicsml container-simready container-simready-workflow container-simready-local-ai container-smoke container-smoke-physicsml container-smoke-simready container-smoke-simready-workflow container-smoke-simready-local-ai container-smoke-all container-push container-push-mesh-cfd container-push-simready container-push-simready-workflow container-push-simready-local-ai
.PHONY: 917-rotating-assembly-f35-test 917-rotating-assembly-f35 917-rotating-assembly-usd-f35-test 917-rotating-assembly-usd-f35 917-intel-cpu-f35-test 917-gmsh-mesh-f35-test 917-gmsh-mesh-f35-image 917-gmsh-mesh-f35-smoke 917-openfoam-engine-f35-test 917-openfoam-engine-f35-image 917-openfoam-engine-f35-smoke 917-gas-path-network-f38-test 917-gas-path-network-f38 917-gas-path-overlay-f38-test 917-gas-path-overlay-f38 917-gas-path-f38-image-test 917-gas-path-f38-image 917-gas-path-f38-image-smoke 917-unsteady-network-f39-test 917-unsteady-network-f39-manifest 917-unsteady-network-f39-validate 917-unsteady-network-f39 917-wave-action-f39-image-test 917-wave-action-f39-image 917-wave-action-f39-image-smoke
.PHONY: 917-unsteady-convergence-f40-test 917-unsteady-convergence-f40-manifest 917-unsteady-convergence-f40-image-smoke 917-unsteady-convergence-f40
.PHONY: 917-extended-periodic-state-f40b-test 917-extended-periodic-state-f40b-manifest 917-extended-periodic-state-f40b-image-smoke 917-extended-periodic-state-f40b
.PHONY: 917-component-factory-f41-test 917-component-factory-f41-plan 917-component-factory-f41-preflight 917-component-factory-f41 917-component-factory-f41-bundle
.PHONY: 917-component-factory-f42a-usd-test
.PHONY: 917-variant-authority-f43-check
.PHONY: 917-connecting-rod-cad-f44-check 917-connecting-rod-cad-f44
.PHONY: 917-valvetrain-material-f45 917-valvetrain-material-f45-check

REGISTRY ?= ghcr.io/cluster2600
IMAGE_TAG ?= dev
PHYSICSNEMO_EXTRAS ?= cu12,sym,mesh-extras,model-extras
VALVE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f
CAD_AUTHOR_F29_IMAGE ?= ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
F31_CAE_IMAGE ?= 3dprinting993-cae-reference-f31:dev
F33_ENGINE_CYCLE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-engine-cycle-f33@sha256:287bd6ea04ff97205cbea9f63b2cc5a7c63ff754b27a183eb482e7896d1e9251
F33_CAE_IMAGE ?= 3dprinting993-cae-integrated-f33:dev
F34B_AIR_OIL_IMAGE ?= 3dprinting993-air-oil-cycle-f34b:dev
F34B_AIR_OIL_RELEASE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-air-oil-cycle-f34b@sha256:369d51ee12c259e844d01817702d8debedcf400087ab9b289b8e59671d296664
F34_CAE_IMAGE ?= 3dprinting993-cae-aircooled-f34:dev
F34_FLUIDX3D_IMAGE ?= 3dprinting993-fluidx3d-aircooled-f34:dev
F37_CAE_IMAGE ?= 3dprinting993-cae-integrated-f33:dev
F37_CAE_IMAGE_ID ?= sha256:4a19fa7d1f253beb3106970ae2635cff85d5aeeaf062aaf807d1dab7b940fb33
F35_CAD_AUTHOR_IMAGE ?= $(CAD_AUTHOR_F29_IMAGE)
F35_SIMREADY_WORKFLOW_IMAGE ?= ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe
F35_GMSH_IMAGE ?= 3dprinting993-gmsh-mesh-f35:dev
F35_OPENFOAM_IMAGE ?= 3dprinting993-openfoam-engine-f35:dev
F38_GAS_PATH_IMAGE ?= 3dprinting993-gas-path-f38:dev
F38_OVERLAY_OUTPUT ?= work/917-gas-path-network-f38/omniverse
F39_WAVE_IMAGE ?= 3dprinting993-wave-action-f39:dev
F39_WAVE_RELEASE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3
F39_OUTPUT ?= work/917-unsteady-network-f39
F40_WAVE_RELEASE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3
F40_OUTPUT ?= work/917-unsteady-convergence-f40
F40_WORKERS ?= 1
F40B_WAVE_RELEASE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3
F40B_OUTPUT ?= work/917-extended-periodic-state-f40b
F41_CAD_IMAGE ?= ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
F41_USD_IMAGE ?= ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe
F41_OUTPUT ?= work/917-component-factory-f41-execution
F41_PLAN_OUTPUT ?= work/917-component-factory-f41-plan
F41_BUNDLE_OUTPUT ?= work/917-component-factory-f41-bundle
override F44_CAD_IMAGE := ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
override F44_OUTPUT := work/917-connecting-rod-cad-f44

.PHONY: 917-scan-conforming-4v-f36-check 917-scan-conforming-4v-f36-assembly 917-scan-conforming-4v-f36-printability 917-scan-conforming-4v-f36-publish 917-scan-conforming-4v-f36-render 917-manufacturing-f37-cad 917-manufacturing-f37-head-mesh 917-manufacturing-f37-head-mesh-enrich 917-manufacturing-f37-screens 917-manufacturing-f37-carrier-fea 917-manufacturing-f37-lpbf-screen 917-manufacturing-f37-lpbf-plan 917-manufacturing-f37-lpbf-audit-check 917-manufacturing-f37-render 917-manufacturing-f37-publish 917-manufacturing-f37-evidence-check 917-f37-simready-evidence-check 917-f37-ice-engine-evidence-check 917-manufacturing-f37-check
.PHONY: 917-f38-brep-lpbf-evidence-check 917-f38-cooling-evidence-check 917-f38-material-coupon-plan-check 917-f38-valvetrain-package-evidence-check 917-f38-engineering-check 917-f40-935-head-reference-check 917-f40-935-scale-audit 917-f40-scan-locked-outer 917-f40-4v-packaging 917-f40-functional-trial 917-f40-thickness-screen 917-f41-lpbf-evidence-check 917-f42-cooling-cht-check 917-f42-brep-audit-test 917-f42-1-topology-repair-test 917-f42-2-pcurve-repair-test 917-f42-1-thermal-optimization-check 917-f42-2-material-process-check 917-f42-omniverse-validation-check 917-f43-g3-g5-comparable-check

F40_PYTHON ?= python3
F42_PYTHON ?= python3
F40_STOCK ?= work/917-scan-conforming-f36/run-013/917-head-scan-stock-f36.local.stl
F40_FLOW_CORE ?= work/917-scan-conforming-f36/run-013/917-head-4v-flow-core-f36.local.stl
F40_CAD ?= twins/reference-917-engine/evidence/f38-valvetrain-package/cad

917-f41-lpbf-evidence-check:
	python3 tests/test_917_f41_lpbf_process.py -v

917-f42-brep-audit-test:
	$(F42_PYTHON) tests/test_917_f42_brep_audit.py -v

917-f42-1-topology-repair-test:
	$(F42_PYTHON) tests/test_917_f42_1_topology_repair.py -v

917-f42-2-pcurve-repair-test:
	$(F42_PYTHON) tests/test_917_f42_2_pcurve_repair.py -v

check: validate test 917-clean-sheet-2026-f32-check 917-air-oil-controls-f34a-check 917-doe-f34-check 917-air-oil-seeds-f34b-check 917-aircooled-4v-f34-check 917-manufacturing-f37-evidence-check 917-manufacturing-f37-lpbf-audit-check 917-f37-simready-evidence-check 917-f41-lpbf-evidence-check 917-f42-cooling-cht-check 917-f42-2-pcurve-repair-test 917-f42-2-material-process-check 917-f42-omniverse-validation-check 917-variant-authority-f43-check 917-connecting-rod-cad-f44-check 917-valvetrain-material-f45-check turbo-cold-side-check turbo-variants-check turbo-dyno-check

917-valvetrain-material-f45:
	python3 twins/reference-917-engine/source/build_valvetrain_material_screen_f45.py --project-root .

917-valvetrain-material-f45-check:
	python3 twins/reference-917-engine/source/build_valvetrain_material_screen_f45.py --project-root . --check
	python3 tests/test_917_valvetrain_material_screen_f45.py -v

validate:
	python3 scripts/validate_catalog.py
	python3 scripts/validate_sources.py
	python3 scripts/validate_measurements.py
	python3 scripts/validate_reference.py
	python3 scripts/validate_manual_measurements.py
	python3 scripts/validate_twin.py
	python3 scripts/validate_specifications.py
	python3 scripts/validate_twins.py
	python3 scripts/validate_components.py
	python3 scripts/validate_engine_sim_contracts.py
	python3 twins/reference-917-engine/source/validate_interfaces_f8.py --project-root .
	python3 twins/reference-917-engine/source/prepare_variant_configs_f10.py --manifest twins/reference-917-engine/variant-configurations-f10.json --project-root . --check

test:
	python3 -m unittest discover -s tests -v

twin:
	python3 scripts/twin_coverage.py

twin-validate:
	python3 scripts/validate_twin.py

engine-contracts:
	docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python -v "$(CURDIR):/workspace" -w /workspace $(VALVE_IMAGE) twins/engine-simulation-contracts/source/refine_segmentation.py --project-root /workspace --config /workspace/twins/engine-simulation-contracts/segmentation-f1.json --output /workspace/work/engine-segmentation-f1

engine-contracts-check:
	python3 scripts/validate_engine_sim_contracts.py

engine-components:
	docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python -v "$(CURDIR):/workspace" -w /workspace $(VALVE_IMAGE) twins/engine-simulation-contracts/source/build_engine_components.py /workspace/work/engine-components-f1

917-complete-parts:
	docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python -v "$(CURDIR):/workspace" -w /workspace $(VALVE_IMAGE) twins/reference-917-engine/source/build_complete_engine_parts.py --config twins/reference-917-engine/complete-engine-f1.json --output work/917-complete-engine/parts

917-complete-assembly: 917-complete-parts
	twins/reference-917-engine/run_complete_engine_pipeline.sh

917-kinematics-f2:
	@test -n "$(F2_INPUT)" || { echo "F2_INPUT=/chemin/vers/scene.usd est requis" >&2; exit 2; }
	twins/reference-917-engine/run_kinematics_f2.sh "$(F2_INPUT)"

917-detail-f3:
	@test -n "$(F2_INPUT)" || { echo "F2_INPUT=/chemin/vers/scene-f2.usd est requis" >&2; exit 2; }
	twins/reference-917-engine/run_detail_expansion_f3.sh "$(F2_INPUT)"

917-virtual-test-bench:
	python3 twins/reference-917-engine/source/run_virtual_test_bench.py \
		--bench twins/reference-917-engine/test-bench-f4.json \
		--systems twins/reference-917-engine/systems-f4.json \
		--support twins/reference-917-engine/start-support-f5.json \
		--output work/917-test-bench/virtual-start-report.json

917-systems-f4:
	@test -n "$(F3_INPUT)" || { echo "F3_INPUT=/chemin/vers/scene-f3.usd est requis" >&2; exit 2; }
	/opt/material-agent/bin/python twins/reference-917-engine/source/build_systems_usd_f4.py "$(F3_INPUT)" \
		--config twins/reference-917-engine/systems-f4.json \
		--output work/917-systems-f4/917-engine-systems-f4.usda
	/opt/material-agent/bin/python twins/reference-917-engine/source/validate_systems_usd_f4.py \
		work/917-systems-f4/917-engine-systems-f4.usda \
		--config twins/reference-917-engine/systems-f4.json \
		--report work/917-systems-f4/validation.json

917-test-bench-usd:
	@test -n "$(F3_INPUT)" || { echo "F3_INPUT=/chemin/vers/scene-f3.usd est requis" >&2; exit 2; }
	/opt/material-agent/bin/python twins/reference-917-engine/source/build_test_bench_usd_f4.py "$(F3_INPUT)" \
		--bench twins/reference-917-engine/test-bench-f4.json \
		--systems twins/reference-917-engine/systems-f4.json \
		--output work/917-test-bench/917-engine-test-bench.usda
	/opt/material-agent/bin/python twins/reference-917-engine/source/validate_test_bench_usd_f4.py \
		work/917-test-bench/917-engine-test-bench.usda \
		--bench twins/reference-917-engine/test-bench-f4.json \
		--report work/917-test-bench/validation.json

917-start-support-f5:
	@test -n "$(F4_INPUT)" || { echo "F4_INPUT=/chemin/vers/scene-banc-systemes.usd est requis" >&2; exit 2; }
	/opt/material-agent/bin/python twins/reference-917-engine/source/build_start_support_usd_f5.py "$(F4_INPUT)" \
		--config twins/reference-917-engine/start-support-f5.json \
		--output work/917-start-support-f5/917-engine-start-support-f5.usda
	/opt/material-agent/bin/python twins/reference-917-engine/source/validate_start_support_usd_f5.py \
		work/917-start-support-f5/917-engine-start-support-f5.usda \
		--config twins/reference-917-engine/start-support-f5.json \
		--report work/917-start-support-f5/validation.json

917-oil-prime-f6:
	python3 twins/reference-917-engine/source/run_oil_prime_0d_f6.py \
		--config twins/reference-917-engine/oil-prime-f6.json \
		--output work/917-oil-prime-f6/input-audit.json

917-motion-video-stages-f7:
	@test -n "$(F5_INPUT)" || { echo "F5_INPUT=/chemin/vers/scene-f5.usd est requis" >&2; exit 2; }
	/opt/material-agent/bin/python twins/reference-917-engine/source/build_motion_video_stages_f7.py "$(F5_INPUT)" \
		--config twins/reference-917-engine/motion-video-f7.json \
		--output-dir work/917-motion-video-f7/stages

917-motion-video-render-f7:
	python3 twins/reference-917-engine/source/render_motion_video_f7.py \
		--config twins/reference-917-engine/motion-video-f7.json \
		--stages-dir work/917-motion-video-f7/stages \
		--output-dir work/917-motion-video-f7/render

917-interfaces-f8-check:
	python3 twins/reference-917-engine/source/validate_interfaces_f8.py --project-root .

917-interfaces-f8-preflight: 917-interfaces-f8-check
	python3 twins/reference-917-engine/source/run_interfaces_preflight_f8.py \
		--project-root . \
		--output work/917-interfaces-f8/input-audit.json

917-performance-envelope-f9:
	python3 twins/reference-917-engine/source/model_performance_envelope_0d_f9.py \
		--config twins/reference-917-engine/performance-target-f9.json \
		--output work/917-performance-f9/power-requirement-envelopes.json

917-variant-geometry-f10-check:
	python3 twins/reference-917-engine/source/prepare_variant_configs_f10.py \
		--manifest twins/reference-917-engine/variant-configurations-f10.json \
		--project-root . --check

917-variant-geometry-f10: 917-variant-geometry-f10-check
	twins/reference-917-engine/run_variant_geometry_f10.sh

917-reengineering-f11:
	python3 twins/reference-917-engine/source/build_reengineering_readiness_f11.py \
		--project-root . \
		--contract twins/reference-917-engine/reengineering-contract-f11.json \
		--inputs twins/reference-917-engine/engineering-inputs-f11.template.json \
		--output work/917-reengineering-f11/readiness.json

917-clean-sheet-head-f29:
	python3 twins/reference-917-engine/source/run_clean_sheet_head_trade_study_f29.py \
		--contract twins/reference-917-engine/clean-sheet-cylinder-head-f29.json \
		--output work/917-clean-sheet-head-f29/design-study.json
	mkdir -p work/917-clean-sheet-head-f29/cad
	chmod 0777 work/917-clean-sheet-head-f29/cad
	docker run --rm --platform linux/amd64 \
		--network none --read-only --tmpfs /tmp:rw,nosuid,size=512m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		--mount type=bind,src="$(CURDIR)",dst=/workspace,readonly \
		--mount type=bind,src="$(CURDIR)/work/917-clean-sheet-head-f29/cad",dst=/output \
		--entrypoint python $(CAD_AUTHOR_F29_IMAGE) \
		/workspace/twins/reference-917-engine/source/build_clean_sheet_head_cad_f29.py \
		--contract /workspace/twins/reference-917-engine/clean-sheet-cylinder-head-f29.json \
		--study /workspace/work/917-clean-sheet-head-f29/design-study.json \
		--toolchain-lock /workspace/containers/cad-author-f28.lock.json \
		--output-dir /output

917-clean-sheet-head-f29-check:
	python3 twins/reference-917-engine/source/validate_clean_sheet_head_f29.py \
		--contract twins/reference-917-engine/clean-sheet-cylinder-head-f29.json \
		--study work/917-clean-sheet-head-f29/design-study.json \
		--geometry-report work/917-clean-sheet-head-f29/cad/geometry-report.json \
		--preflight work/917-clean-sheet-head-f29/omniverse/preflight.json \
		--handoff twins/reference-917-engine/omniverse-handoff-f29.json \
		--output work/917-clean-sheet-head-f29/report.json

917-clean-sheet-head-f29-figures:
	python3 twins/reference-917-engine/source/render_clean_sheet_head_results_f29.py \
		--evidence-root twins/reference-917-engine/evidence/f29 \
		--output-dir twins/reference-917-engine/evidence/f29/figures

917-head-reference-cae-f31-image:
	docker build -f containers/cae-reference-f31.Dockerfile -t $(F31_CAE_IMAGE) .

917-head-reference-cae-f31:
	@test ! -e work/917-head-reference-cae-f31 || { echo "work/917-head-reference-cae-f31 existe déjà; conserver ou déplacer le run avant de relancer" >&2; exit 2; }
	docker run --rm --network none --read-only --cap-drop ALL \
		--security-opt no-new-privileges --user "$$(id -u):$$(id -g)" \
		--tmpfs /tmp:rw,noexec,nosuid,size=256m \
		-v "$(CURDIR):/workspace:rw" $(F31_CAE_IMAGE) \
		/workspace/twins/reference-917-engine/source/run_head_reference_fea_f31.py \
		--root /workspace \
		--contract /workspace/twins/reference-917-engine/head-reference-cae-f31.json \
		--output /workspace/work/917-head-reference-cae-f31

917-head-reference-cae-f31-publish:
	python3 twins/reference-917-engine/source/render_head_reference_fea_f31.py \
		--report work/917-head-reference-cae-f31/report.json \
		--output twins/reference-917-engine/evidence/f31

917-clean-sheet-2026-f32:
	python3 twins/reference-917-engine/source/run_clean_sheet_2026_f32.py \
		--contract twins/reference-917-engine/clean-sheet-2026-f32.json \
		--output work/917-clean-sheet-2026-f32/screening-report.json

917-clean-sheet-2026-f32-check:
	python3 twins/reference-917-engine/source/run_clean_sheet_2026_f32.py \
		--contract twins/reference-917-engine/clean-sheet-2026-f32.json \
		--check twins/reference-917-engine/evidence/f32/screening-report.json

917-cycle-thermal-f33:
	mkdir -p work/917-cycle-thermal-f33
	chmod 0777 work/917-cycle-thermal-f33
	docker run --rm --platform linux/amd64 --user 9133:9133 \
		--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		--mount type=bind,src="$(CURDIR)",dst=/workspace,readonly \
		--mount type=bind,src="$(CURDIR)/work/917-cycle-thermal-f33",dst=/output \
		$(F33_ENGINE_CYCLE_IMAGE) \
		python /workspace/scripts/run_917_cycle_thermal_f33.py \
		--contract /workspace/twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json \
		--output /output/cycle-thermal-report.json

917-cycle-thermal-f33-check:
	docker run --rm --platform linux/amd64 --user 9133:9133 \
		--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		--mount type=bind,src="$(CURDIR)",dst=/workspace,readonly \
		$(F33_ENGINE_CYCLE_IMAGE) \
		python /workspace/scripts/run_917_cycle_thermal_f33.py \
		--contract /workspace/twins/reference-917-engine/clean-sheet-cycle-thermal-f33.json \
		--check /workspace/twins/reference-917-engine/evidence/f33/cycle-thermal-report.json

917-cycle-thermal-f33-test:
	docker run --rm --platform linux/amd64 --user 9133:9133 \
		--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=128m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		--mount type=bind,src="$(CURDIR)",dst=/workspace,readonly \
		-w /workspace $(F33_ENGINE_CYCLE_IMAGE) \
		python tests/test_917_cycle_thermal_f33.py -v

917-air-oil-controls-f34a-check:
	python3 scripts/validate_917_air_oil_core_controls_f34a.py \
		--contract twins/reference-917-engine/air-oil-core-controls-f34a.json

917-air-oil-controls-f34a-test:
	python3 tests/test_917_air_oil_core_controls_f34a.py -v

917-doe-f34:
	mkdir -p work/917-doe-f34
	python3 scripts/run_917_doe_f34.py \
		--contract twins/reference-917-engine/doe-surrogate-f34.json \
		--output work/917-doe-f34/doe-case-manifest.json

917-doe-f34-check:
	python3 scripts/run_917_doe_f34.py \
		--contract twins/reference-917-engine/doe-surrogate-f34.json \
		--check twins/reference-917-engine/evidence/f34/doe-case-manifest.json

917-doe-f34-test:
	python3 tests/test_917_doe_f34.py -v

917-air-oil-seeds-f34b:
	python3 scripts/export_917_air_oil_seeds_f34b.py \
		--output twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json

917-air-oil-seeds-f34b-check:
	python3 scripts/export_917_air_oil_seeds_f34b.py \
		--check twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json

917-air-oil-cycle-f34b-preflight: 917-air-oil-seeds-f34b-check
	mkdir -p work/917-air-oil-cycle-f34b
	python3 scripts/run_917_air_oil_cycle_f34b.py preflight \
		--doe-contract twins/reference-917-engine/doe-surrogate-f34.json \
		--architecture-contract twins/reference-917-engine/air-oil-core-controls-f34a.json \
		--seed-bundle twins/reference-917-engine/evidence/f34/air-oil-forward-seeds-f34b.json \
		--output work/917-air-oil-cycle-f34b/preflight.json

917-air-oil-cycle-f34b-test:
	python3 tests/test_917_air_oil_seeds_f34b.py -v
	python3 tests/test_917_air_oil_cycle_f34b.py -v

917-air-oil-cycle-f34b-image-test:
	python3 tests/test_air_oil_cycle_f34b_image.py -v

917-air-oil-cycle-f34b-lock-check:
	python3 tests/test_air_oil_cycle_f34b_lock.py -v

917-air-oil-cycle-f34b-image: 917-air-oil-seeds-f34b-check 917-air-oil-cycle-f34b-image-test
	docker buildx build --platform linux/amd64 \
		-f containers/air-oil-cycle-f34b.Dockerfile \
		-t $(F34B_AIR_OIL_IMAGE) --load .

917-air-oil-cycle-f34b-smoke:
	docker run --rm --platform linux/amd64 --user 9133:9133 \
		--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		$(F34B_AIR_OIL_IMAGE)

917-rotating-assembly-f35-test:
	python3 tests/test_917_rotating_assembly_cad_f35.py -v
	python3 tests/test_917_rotating_assembly_usd_f35.py -v
	python3 tests/test_917_rotating_assembly_usd_f35_runner.py -v

917-rotating-assembly-f35: 917-rotating-assembly-f35-test
	mkdir -p work/917-rotating-assembly-f35
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,noexec,nosuid,nodev,size=512m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-e HOME=/tmp -e XDG_CACHE_HOME=/tmp/cad-author-cache \
		-e F35_CAD_RUNTIME_IMAGE_REF="$(F35_CAD_AUTHOR_IMAGE)" \
		--mount type=bind,src="$(CURDIR)/twins",dst=/workspace/twins,readonly \
		--mount type=bind,src="$(CURDIR)/work",dst=/workspace/work \
		--workdir /workspace --entrypoint python $(F35_CAD_AUTHOR_IMAGE) \
		/workspace/twins/reference-917-engine/source/build_rotating_assembly_cad_f35.py \
		--contract /workspace/twins/reference-917-engine/rotating-assembly-cad-f35.json \
		--output /workspace/work/917-rotating-assembly-f35

917-rotating-assembly-usd-f35-test:
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,noexec,nosuid,nodev,size=1g \
		--pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
		-e HOME=/tmp -e XDG_CACHE_HOME=/tmp/simready-cache \
		--mount type=bind,src="$(CURDIR)",dst=/workspace,readonly \
		--workdir /workspace --entrypoint /opt/simready-validation/bin/python \
		$(F35_SIMREADY_WORKFLOW_IMAGE) tests/test_917_rotating_assembly_usd_f35.py -v

917-rotating-assembly-usd-f35: 917-rotating-assembly-f35
	F35_SIMREADY_WORKFLOW_IMAGE_REF=$(F35_SIMREADY_WORKFLOW_IMAGE) \
		twins/reference-917-engine/source/run_rotating_assembly_usd_f35.sh

917-intel-cpu-f35-test:
	python3 tests/test_intel_cpu_node_f35.py -v
	python3 tests/test_intel_cpu_smokes_f35.py -v

917-gmsh-mesh-f35-test:
	python3 tests/test_gmsh_mesh_f35_image.py -v
	python3 tests/test_gmsh_mesh_f35_lock.py -v

917-gmsh-mesh-f35-image: 917-gmsh-mesh-f35-test
	docker buildx build --platform linux/amd64 \
		-f containers/gmsh-mesh-f35.Dockerfile \
		-t $(F35_GMSH_IMAGE) --load .

917-gmsh-mesh-f35-smoke:
	docker run --rm --platform linux/amd64 --user 9135:9135 \
		--network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		$(F35_GMSH_IMAGE)

917-openfoam-engine-f35-test:
	python3 tests/test_openfoam_engine_f35_image.py -v
	python3 tests/test_openfoam_engine_f35_lock.py -v

917-openfoam-engine-f35-image: 917-openfoam-engine-f35-test
	docker buildx build --platform linux/amd64 \
		-f containers/openfoam-engine-f35.Dockerfile \
		-t $(F35_OPENFOAM_IMAGE) --load .

917-openfoam-engine-f35-smoke:
	docker run --rm --platform linux/amd64 --user 9135:9135 \
		--network none --read-only \
		--tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
		--tmpfs /dev/shm:rw,noexec,nosuid,nodev,size=512m \
		--pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
		$(F35_OPENFOAM_IMAGE)

917-gas-path-network-f38-test:
	python3 tests/test_917_gas_path_network_f38.py -v

917-gas-path-network-f38: 917-gas-path-network-f38-test
	python3 twins/reference-917-engine/source/run_gas_path_network_f38.py \
		--project-root . \
		--contract twins/reference-917-engine/gas-path-network-f38.json \
		--output work/917-gas-path-network-f38

917-gas-path-overlay-f38-test:
	python3 tests/test_917_gas_path_overlay_f38.py -v

917-gas-path-overlay-f38: 917-gas-path-network-f38 917-gas-path-overlay-f38-test
	@test -f work/917-integrated-bench-f37/integrated-bench-f37-report.json || { echo "Exécuter F37 avant l'overlay F38" >&2; exit 2; }
	python3 twins/reference-917-engine/source/author_bench_overlay_f38.py \
		--contract twins/reference-917-engine/gas-path-network-f38.json \
		--f37-work-root work/917-integrated-bench-f37 \
		--f38-report work/917-gas-path-network-f38/gas-path-network-f38-report.json \
		--canonical-f38-report twins/reference-917-engine/evidence/f38/gas-path-network-f38-report.json \
		--output $(F38_OVERLAY_OUTPUT)

917-gas-path-f38-image-test:
	python3 tests/test_gas_path_f38_image.py -v

917-gas-path-f38-image: 917-gas-path-network-f38-test 917-gas-path-f38-image-test
	docker buildx build --platform linux/amd64 \
		-f containers/gas-path-f38.Dockerfile \
		-t $(F38_GAS_PATH_IMAGE) --load .

917-gas-path-f38-image-smoke:
	docker run --rm --platform linux/amd64 --user 9138:9138 \
		--network none --read-only \
		--tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
		--pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
		$(F38_GAS_PATH_IMAGE)

917-unsteady-network-f39-test:
	python3 tests/test_917_unsteady_network_f39.py -v
	python3 tests/test_917_engine_wave_f39_image.py -v

917-unsteady-network-f39-manifest: 917-unsteady-network-f39-test
	python3 twins/reference-917-engine/source/run_unsteady_network_f39.py \
		--project-root . \
		--contract twins/reference-917-engine/unsteady-network-f39.json \
		--output-dir $(F39_OUTPUT)

917-unsteady-network-f39-validate: 917-unsteady-network-f39-test
	mkdir -p $(F39_OUTPUT)
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=256m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -v "$(CURDIR)/$(F39_OUTPUT):/output:rw" \
		--entrypoint python $(F39_WAVE_RELEASE_IMAGE) \
		/workspace/twins/reference-917-engine/source/run_unsteady_network_f39.py \
		--project-root /workspace \
		--contract /workspace/twins/reference-917-engine/unsteady-network-f39.json \
		--output-dir /output --validate-aeolus

917-unsteady-network-f39: 917-unsteady-network-f39-test
	mkdir -p $(F39_OUTPUT)
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=512m \
		--pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -v "$(CURDIR)/$(F39_OUTPUT):/output:rw" \
		--entrypoint python $(F39_WAVE_RELEASE_IMAGE) \
		/workspace/twins/reference-917-engine/source/run_unsteady_network_f39.py \
		--project-root /workspace \
		--contract /workspace/twins/reference-917-engine/unsteady-network-f39.json \
		--output-dir /output --execute

917-unsteady-convergence-f40-test:
	python3 tests/test_917_unsteady_convergence_f40.py -v

917-unsteady-convergence-f40-manifest: 917-unsteady-convergence-f40-test
	python3 twins/reference-917-engine/source/run_unsteady_convergence_f40.py \
		--project-root . \
		--contract twins/reference-917-engine/unsteady-convergence-campaign-f40.json \
		--output-dir $(F40_OUTPUT) --manifest

917-unsteady-convergence-f40-image-smoke:
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=512m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -w /workspace \
		--entrypoint python $(F40_WAVE_RELEASE_IMAGE) \
		tests/test_917_unsteady_convergence_f40.py -v

917-unsteady-convergence-f40: 917-unsteady-convergence-f40-test
	mkdir -p "$(abspath $(F40_OUTPUT))"
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=1024m \
		--pids-limit 256 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -v "$(abspath $(F40_OUTPUT)):/output:rw" \
		--entrypoint python $(F40_WAVE_RELEASE_IMAGE) \
		/workspace/twins/reference-917-engine/source/run_unsteady_convergence_f40.py \
		--project-root /workspace \
		--contract /workspace/twins/reference-917-engine/unsteady-convergence-campaign-f40.json \
		--output-dir /output --execute --workers $(F40_WORKERS)

917-extended-periodic-state-f40b-test:
	python3 tests/test_917_extended_periodic_state_f40b.py -v

917-extended-periodic-state-f40b-manifest: 917-extended-periodic-state-f40b-test
	python3 twins/reference-917-engine/source/run_extended_periodic_state_f40b.py \
		--project-root . \
		--contract twins/reference-917-engine/extended-periodic-state-f40b.json \
		--output-dir $(F40B_OUTPUT) --manifest

917-extended-periodic-state-f40b-image-smoke:
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=512m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -w /workspace \
		--entrypoint python $(F40B_WAVE_RELEASE_IMAGE) \
		tests/test_917_extended_periodic_state_f40b.py -v

917-extended-periodic-state-f40b: 917-extended-periodic-state-f40b-test
	mkdir -p "$(abspath $(F40B_OUTPUT))"
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=1024m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-v "$(CURDIR):/workspace:ro" -v "$(abspath $(F40B_OUTPUT)):/output:rw" \
		--entrypoint python $(F40B_WAVE_RELEASE_IMAGE) \
		/workspace/twins/reference-917-engine/source/run_extended_periodic_state_f40b.py \
		--project-root /workspace \
		--contract /workspace/twins/reference-917-engine/extended-periodic-state-f40b.json \
		--output-dir /output --execute

917-component-factory-f41-test:
	python3 tests/test_917_component_factory_f41.py -v

917-component-factory-f41-plan: 917-component-factory-f41-test
	test ! -e "$(F41_PLAN_OUTPUT)"
	python3 twins/reference-917-engine/source/build_component_factory_f41.py \
		--project-root . \
		--contract twins/reference-917-engine/component-factory-f41.json \
		--output "$(F41_PLAN_OUTPUT)"

917-component-factory-f41-preflight: 917-component-factory-f41-test
	F41_CAD_IMAGE_REF="$(F41_CAD_IMAGE)" \
	F41_USD_IMAGE_REF="$(F41_USD_IMAGE)" \
		twins/reference-917-engine/source/run_component_factory_f41.sh --preflight-only

917-component-factory-f41: 917-component-factory-f41-test
	F41_CAD_IMAGE_REF="$(F41_CAD_IMAGE)" \
	F41_USD_IMAGE_REF="$(F41_USD_IMAGE)" \
	F41_OUTPUT="$(abspath $(F41_OUTPUT))" \
		twins/reference-917-engine/source/run_component_factory_f41.sh

917-component-factory-f41-bundle: 917-component-factory-f41-test
	test ! -e "$(F41_BUNDLE_OUTPUT)"
	python3 twins/reference-917-engine/source/build_component_factory_bundle_f41.py \
		--project-root . --output "$(F41_BUNDLE_OUTPUT)"

917-component-factory-f42a-usd-test:
	PYTHONDONTWRITEBYTECODE=1 python3 tests/test_917_component_factory_f42a_usd.py -v

917-variant-authority-f43-check:
	PYTHONDONTWRITEBYTECODE=1 python3 twins/reference-917-engine/source/validate_variant_authority_f43.py \
		--project-root . \
		--contract twins/reference-917-engine/variant-authority-f43.json
	PYTHONDONTWRITEBYTECODE=1 python3 tests/test_917_variant_authority_f43.py -v

917-connecting-rod-cad-f44-check:
	PYTHONDONTWRITEBYTECODE=1 python3 twins/reference-917-engine/source/validate_connecting_rod_cad_f44.py \
		--project-root . \
		--contract twins/reference-917-engine/connecting-rod-cad-f44.json
	PYTHONDONTWRITEBYTECODE=1 python3 tests/test_917_connecting_rod_cad_f44.py -v

917-connecting-rod-cad-f44: 917-connecting-rod-cad-f44-check
	test ! -L work
	test ! -L "$(F44_OUTPUT)"
	test ! -e "$(F44_OUTPUT)"
	mkdir -p work
	test -d work
	docker run --rm --platform linux/amd64 --user "$$(id -u):$$(id -g)" \
		--network none --read-only \
		--tmpfs /tmp:rw,noexec,nosuid,nodev,size=512m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		-e HOME=/tmp -e XDG_CACHE_HOME=/tmp/cad-author-cache \
		-e F44_CAD_RUNTIME_IMAGE_REF="$(F44_CAD_IMAGE)" \
		--mount type=bind,src="$(CURDIR)/twins",dst=/workspace/twins,readonly \
		--mount type=bind,src="$(CURDIR)/work",dst=/workspace/work \
		--workdir /workspace --entrypoint python "$(F44_CAD_IMAGE)" \
		/workspace/twins/reference-917-engine/source/smoke_connecting_rod_cad_f44.py \
		--project-root /workspace \
		--contract /workspace/twins/reference-917-engine/connecting-rod-cad-f44.json \
		--output "/workspace/$(F44_OUTPUT)"

917-wave-action-f39-image-test:
	python3 tests/test_917_engine_wave_f39_image.py -v

917-wave-action-f39-image: 917-wave-action-f39-image-test
	docker buildx build --platform linux/amd64 \
		-f containers/917-engine-wave-f39/Dockerfile \
		-t $(F39_WAVE_IMAGE) --load .

917-wave-action-f39-image-smoke:
	docker run --rm --platform linux/amd64 --user 9139:9139 \
		--network none --read-only \
		--tmpfs /tmp:rw,exec,nosuid,nodev,size=256m \
		--pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
		$(F39_WAVE_IMAGE)

917-integrated-virtual-f33-image:
	docker build -f containers/cae-integrated-f33.Dockerfile -t $(F33_CAE_IMAGE) .

917-integrated-virtual-f33:
	F33_CAE_IMAGE=$(F33_CAE_IMAGE) twins/reference-917-engine/source/run_integrated_virtual_validation_f33.sh \
		work/917-integrated-virtual-f33

917-integrated-virtual-f33-publish:
	python3 twins/reference-917-engine/source/render_integrated_virtual_validation_f33.py \
		--report work/917-integrated-virtual-f33/report.json \
		--geometry-report work/917-integrated-virtual-f33/functional-cad/geometry-report.json \
		--product-stl work/917-integrated-virtual-f33/functional-cad/917-head-functional-solver-4v.stl \
		--container-image work/917-integrated-virtual-f33/openfoam/container-image.json \
		--x86-cross-check work/917-integrated-virtual-f33/toolchain/x86-cross-check.json \
		--preflight-json work/917-integrated-virtual-f33/omniverse/preflight.json \
		--preflight-markdown work/917-integrated-virtual-f33/omniverse/preflight.md \
		--output twins/reference-917-engine/evidence/f33

917-aircooled-4v-f34-cae-image:
	docker build -f containers/cae-aircooled-f34.Dockerfile -t $(F34_CAE_IMAGE) .

917-aircooled-4v-f34-fluidx3d-image:
	docker build -f containers/fluidx3d-aircooled-f34.Dockerfile -t $(F34_FLUIDX3D_IMAGE) .

917-aircooled-4v-f34-check:
	python3 tests/test_917_aircooled_4v_f34.py -v

917-scan-conforming-4v-f36-check:
	python3 tests/test_917_scan_conforming_4v_f36.py -v

917-scan-conforming-4v-f36-assembly:
	docker run --rm --platform linux/amd64 --network none --user 9133:9133 \
		-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mpl \
		-v "$(CURDIR):/workspace" -w /workspace --entrypoint /opt/venv/bin/python $(VALVE_IMAGE) \
		twins/reference-917-engine/source/analyze_f36_valvetrain_assembly.py \
		--head work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--contract twins/reference-917-engine/f36-valvetrain-assembly.json \
		--output work/917-scan-conforming-f36/valvetrain-013

917-scan-conforming-4v-f36-printability:
	docker run --rm --platform linux/amd64 --network none --user 9133:9133 \
		-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mpl \
		-v "$(CURDIR):/workspace" -w /workspace --entrypoint /opt/venv/bin/python $(VALVE_IMAGE) \
		twins/reference-917-engine/source/analyze_f36_lpbf_printability.py \
		--head work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--output work/917-scan-conforming-f36/lpbf-013

917-scan-conforming-4v-f36-publish:
	python3 twins/reference-917-engine/source/summarize_scan_conforming_cae_f36.py \
		--cases work/917-scan-conforming-f36/openfoam-massflow-002/cases.json \
		--calculix work/917-scan-conforming-f36/calculix-burst-001/hexa-4p0-v5/report.json work/917-scan-conforming-f36/calculix-burst-001/hexa-3p0-v1/report.json work/917-scan-conforming-f36/calculix-burst-001/hexa-2p5-v1/report.json \
		--fluidx3d work/917-scan-conforming-f36/fluidx3d-burst-001/coarse-domain-v3.json work/917-scan-conforming-f36/fluidx3d-burst-001/medium-domain-v3.json \
		--fluidx3d-sensitivity work/917-scan-conforming-f36/fluidx3d-burst-001/coarse-domain-alpha1e-3-v3.json work/917-scan-conforming-f36/fluidx3d-burst-001/coarse-domain-alpha3e-3-v3.json work/917-scan-conforming-f36/fluidx3d-burst-001/coarse-domain-alpha6e-3-v3.json \
		--cycle work/917-cycle-thermal-f33/cycle-thermal-report.json \
		--two-four-valve-report work/917-integrated-virtual-f33-f36-rerun/report.json \
		--output twins/reference-917-engine/evidence/f36/recalculation-report.json

917-scan-conforming-4v-f36-render:
	python3 twins/reference-917-engine/source/render_scan_conforming_cae_f36.py \
		--stl work/917-scan-conforming-f36/run-007/917-head-scan-stock-f36.local.stl \
		--product-image work/917-scan-conforming-f36/run-007/917-head-scan-conforming-4v-f36.png \
		--report twins/reference-917-engine/evidence/f36/recalculation-report.json \
		--output work/917-scan-conforming-f36/f36-recalculation-board.png

917-manufacturing-f37-cad:
	docker run --rm --platform linux/amd64 --network none \
		-e HOME=/tmp -v "$(CURDIR):/workspace" -w /workspace \
		--entrypoint python3 $(CAD_AUTHOR_F29_IMAGE) \
		twins/reference-917-engine/source/build_f37_manufacturing_definition.py \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--head-stl work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
		--output work/917-scan-conforming-f37/cad

917-manufacturing-f37-head-mesh:
	docker run --rm --platform linux/amd64 --network none \
		-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mpl \
		-v "$(CURDIR):/workspace" -w /workspace \
		--entrypoint /opt/venv/bin/python $(VALVE_IMAGE) \
		twins/reference-917-engine/source/build_f37_printable_head_mesh.py \
		--head work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
		--flow-core work/917-scan-conforming-f36/run-013/917-head-4v-flow-core-f36.local.stl \
		--oil-core work/917-scan-conforming-f37/cad/oil-gallery-core.stl \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
		--output work/917-scan-conforming-f37/head-mesh-proof

917-manufacturing-f37-head-mesh-enrich:
	python3 twins/reference-917-engine/source/enrich_f37_head_mesh_nvidia.py \
		--report work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json \
		--head work/917-scan-conforming-f37/head-mesh-proof/917-head-f37-printable-proof.local.stl \
		--attestation work/917-scan-conforming-f37/nvidia-repair-candidate/f37-nvidia-geometry-validation-attestation.json

917-manufacturing-f37-screens:
	python3 twins/reference-917-engine/source/screen_f37_rocker_kinematics.py \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
		--valve-lift-mm 12 \
		--output work/917-scan-conforming-f37/kinematics
	python3 twins/reference-917-engine/source/screen_f37_oil_system.py \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--output work/917-scan-conforming-f37/oil
	python3 twins/reference-917-engine/source/screen_f37_carrier_strength.py \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--kinematics work/917-scan-conforming-f37/kinematics/f37-rocker-kinematic-report.json \
		--output work/917-scan-conforming-f37/strength

917-manufacturing-f37-lpbf-screen:
	docker run --rm --platform linux/amd64 --network none \
		-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mpl \
		-v "$(CURDIR):/workspace" -w /workspace \
		--entrypoint /opt/venv/bin/python $(VALVE_IMAGE) \
		twins/reference-917-engine/source/analyze_f36_lpbf_printability.py \
		--head work/917-scan-conforming-f37/head-mesh-proof/917-head-f37-printable-proof.local.stl \
		--voxel-pitch-mm 4.0 \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--phase F37 \
		--output work/917-scan-conforming-f37/lpbf-exact

917-manufacturing-f37-carrier-fea:
	test "$$(docker image inspect $(F37_CAE_IMAGE) --format '{{.Id}}')" = "$(F37_CAE_IMAGE_ID)"
	docker run --rm --network none \
		-e HOME=/tmp -v "$(CURDIR):/workspace" -w /workspace \
		--entrypoint python3 \
		$(F37_CAE_IMAGE) \
		twins/reference-917-engine/source/run_f37_carrier_calculix.py \
		--step work/917-scan-conforming-f37/cad/rocker-carrier-as-printed.step \
		--contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--geometry-report work/917-scan-conforming-f36/run-013/geometry-report.json \
		--mesh-sizes 2.0,1.5,1.25 \
		--runtime-image-ref $(F37_CAE_IMAGE) \
		--runtime-image-id $(F37_CAE_IMAGE_ID) \
		--output work/917-scan-conforming-f37/carrier-calculix

917-manufacturing-f37-lpbf-plan:
	python3 twins/reference-917-engine/source/compile_f37_lpbf_manufacturing_plan.py \
		--printability work/917-scan-conforming-f37/lpbf-exact/lpbf-printability-report.json \
		--f37-head-mesh-report work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json \
		--locked-plate work/917-scan-conforming-f36/lpbf-locked-plate-p3/report.json \
		--f37-contract twins/reference-917-engine/f37-manufacturing-definition.json \
		--f37-cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
		--output work/917-scan-conforming-f37/lpbf

917-manufacturing-f37-lpbf-audit-check:
	docker run --rm --platform linux/amd64 --network none \
		-e HOME=/tmp -e MPLCONFIGDIR=/tmp/mpl \
		-v "$(CURDIR):/workspace" -w /workspace \
		--entrypoint /opt/venv/bin/python $(VALVE_IMAGE) \
		tests/test_917_f37_lpbf_voxel_audit.py -v

917-manufacturing-f37-render:
	python3 twins/reference-917-engine/source/render_f37_manufacturing_definition.py \
		--head work/917-scan-conforming-f36/run-013/917-head-scan-conforming-4v-f36.local.stl \
		--cad-dir work/917-scan-conforming-f37/cad \
		--output work/917-scan-conforming-f37/917-head-f37-manufacturing-definition.png

917-manufacturing-f37-publish:
	python3 twins/reference-917-engine/source/publish_f37_manufacturing_evidence.py \
		--project-root .

917-manufacturing-f37-evidence-check:
	python3 tests/test_917_f37_published_evidence.py -v

917-f37-simready-evidence-check:
	python3 tests/test_917_f37_simready_evidence.py -v

917-f37-ice-engine-evidence-check:
	python3 tests/test_917_f37_ice_engine_foam.py -v

917-manufacturing-f37-check: 917-manufacturing-f37-evidence-check
	test -f work/917-scan-conforming-f37/cad/f37-cad-report.json
	test -f work/917-scan-conforming-f37/kinematics/f37-rocker-kinematic-report.json
	test -f work/917-scan-conforming-f37/oil/f37-oil-hydraulic-report.json
	test -f work/917-scan-conforming-f37/strength/f37-carrier-strength-report.json
	test -f work/917-scan-conforming-f37/carrier-calculix/f37-carrier-calculix-report.json
	test -f work/917-scan-conforming-f37/lpbf/f37-lpbf-manufacturing-report.json
	test -f work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json
	F37_EVIDENCE_DIR=work/917-scan-conforming-f37/cad \
		python3 tests/test_917_f37_manufacturing_definition.py -v

917-f38-brep-lpbf-evidence-check:
	python3 tests/test_917_f38_brep_lpbf.py -v

917-f38-valvetrain-package-evidence-check:
	python3 tests/test_917_f38_valvetrain_package.py -v

917-f38-cooling-evidence-check:
	python3 tests/test_917_f38_cooling_redesign.py -v

917-f38-material-coupon-plan-check:
	python3 tests/test_917_f38_material_coupon_plan.py -v

917-f38-engineering-check:
	python3 tests/test_917_f38_engineering_checkpoint.py -v

917-f39-scan-only-program-check:
	python3 tests/test_917_f39_scan_only_program.py -v

917-f39-cooling-optimization-check:
	python3 tests/test_917_f39_cooling_optimization.py -v

917-f42-cooling-cht-check:
	python3 tests/test_917_f42_cooling_cht.py -v

917-f42-1-thermal-optimization-check:
	python3 tests/test_917_f42_1_thermal_optimization.py -v

917-f42-omniverse-validation-check:
	python3 tests/test_917_f42_omniverse_validation.py -v

917-f42-2-material-process-check:
	python3 tests/test_917_f42_2_material_process.py -v

917-f43-g3-g5-comparable-check:
	python3 twins/reference-917-engine/source/audit_g3_g5_comparable_execution_f43.py --check twins/reference-917-engine/evidence/f43-g3-g5-comparable/audit-report.json
	python3 tests/test_917_f43_g3_g5_comparable.py -v

917-f39-lpbf-structural-check:
	python3 tests/test_917_f39_lpbf_structural.py -v

917-f39-brep-scan-only-check:
	python3 tests/test_917_f39_brep_scan_only.py -v

917-f39-functional-video-check:
	python3 tests/test_917_f39_functional_video.py -v

917-f39-check: 917-f39-scan-only-program-check 917-f39-brep-scan-only-check 917-f39-cooling-optimization-check 917-f39-lpbf-structural-check 917-f39-functional-video-check

917-f40-935-head-reference-check:
	python3 tests/test_917_f40_935_head_reference.py -v

917-f40-935-scale-audit:
	python3 twins/reference-917-engine/source/audit_935_scan_scale_f40.py \
		--scan work/wolfe-classics-935-cylinder-head/pipeline/input/935-xtreme-cylinder-head-working-copy.obj \
		--envelope work/wolfe-classics-935-cylinder-head/pipeline/segmented/head-envelope-uncapped.ply \
		--interfaces work/wolfe-classics-935-cylinder-head/pipeline/reports/interfaces.json \
		--contract twins/reference-917-engine/935-head-reference-f40.json \
		--output work/917-f40-reference/scale-audit

917-f40-scan-locked-outer:
	$(F40_PYTHON) twins/reference-917-engine/source/build_scan_locked_outer_brep_f40.py \
		--stock $(F40_STOCK) \
		--contract twins/reference-917-engine/935-head-reference-f40.json \
		--output work/917-f40-reference/outer-brep

917-f40-4v-packaging: 917-f40-scan-locked-outer
	$(F40_PYTHON) twins/reference-917-engine/source/render_scan_locked_4v_packaging_f40.py \
		--outer work/917-f40-reference/outer-brep/917-head-935-scan-locked-outer-f40.local.stl \
		--flow-core $(F40_FLOW_CORE) \
		--cad $(F40_CAD) \
		--output work/917-f40-reference/packaging

917-f40-functional-trial: 917-f40-scan-locked-outer
	$(F40_PYTHON) twins/reference-917-engine/source/build_scan_locked_functional_trial_f40.py \
		--outer work/917-f40-reference/outer-brep/917-head-935-scan-locked-outer-f40.local.stl \
		--flow-core $(F40_FLOW_CORE) \
		--interfaces work/wolfe-classics-935-cylinder-head/pipeline/reports/interfaces.json \
		--output work/917-f40-reference/functional-trial

917-f40-thickness-screen: 917-f40-functional-trial
	$(F40_PYTHON) twins/reference-917-engine/source/audit_scan_locked_functional_f40.py \
		--head work/917-f40-reference/functional-trial/917-head-935-scan-locked-functional-trial-f40.local.stl \
		--functional-report work/917-f40-reference/functional-trial/917-head-935-scan-locked-functional-trial-f40-report.json \
		--output work/917-f40-reference/thickness-screen

917-aircooled-4v-f34-publish:
	python3 twins/reference-917-engine/source/publish_aircooled_4v_f34.py \
		--contract twins/reference-917-engine/aircooled-4v-scan-f34.json \
		--geometry work/917-aircooled-4v-f34/cad-domain-separated/geometry-report.json \
		--preliminary work/917-aircooled-4v-f34/report-preliminary-v2.json \
		--f33-reference twins/reference-917-engine/evidence/f33/report.json \
		--openfoam-case work/917-aircooled-4v-f34/openfoam-external-skew4/medium \
		--calculix work/917-aircooled-4v-f34/calculix-coarse-v5/report.json work/917-aircooled-4v-f34/calculix-fine-v2/report.json work/917-aircooled-4v-f34/calculix-finer-v2/report.json \
		--fluidx3d work/917-aircooled-4v-f34/fluidx3d-grid96-approved.json work/917-aircooled-4v-f34/fluidx3d-grid192-approved.json work/917-aircooled-4v-f34/fluidx3d-grid384-approved.json \
		--omniverse work/917-aircooled-4v-f34/omniverse/preflight.json \
		--toolchain-audit work/917-aircooled-4v-f34/toolchain-audit.json \
		--step work/917-aircooled-4v-f34/cad-domain-separated/917-head-aircooled-4v-f34.step \
		--image work/917-aircooled-4v-f34/product-aircooled-4v-f34-v2.png \
		--output work/917-aircooled-4v-f34-publication

valve-variants:
	docker run --rm --platform linux/amd64 --entrypoint /opt/venv/bin/python -v "$(CURDIR):/workspace" -w /workspace $(VALVE_IMAGE) twins/reference-935-cylinder-head/source/build_valve_variants.py work/valve-variants-f1

omniverse-assembly:
	twins/omniverse-engine-assembly/run_pipeline.sh

turbo-cold-side:
	python3 scripts/generate_cold_side_case.py --write

turbo-cold-side-check:
	python3 scripts/generate_cold_side_case.py --check

turbo-variants:
	python3 scripts/generate_turbo_variants.py --write

turbo-variants-check:
	python3 scripts/generate_turbo_variants.py --check

turbo-dyno:
	python3 scripts/model_turbo_dyno_0d.py --write

turbo-dyno-check:
	python3 scripts/model_turbo_dyno_0d.py --check

container-recon:
	docker build -f containers/recon.Dockerfile -t 3dprinting993-recon:$(IMAGE_TAG) .

container-cadsim:
	docker build -f containers/cadsim.Dockerfile -t 3dprinting993-cadsim:$(IMAGE_TAG) .

container-mesh-cfd:
	docker build -f containers/mesh-cfd.Dockerfile -t 3dprinting993-mesh-cfd:$(IMAGE_TAG) .

container-physicsml:
	docker build --build-arg PHYSICSNEMO_EXTRAS=$(PHYSICSNEMO_EXTRAS) -f containers/physicsml.Dockerfile -t 3dprinting993-physicsml:$(IMAGE_TAG) .

container-simready:
	docker build --platform linux/amd64 -f containers/simready.Dockerfile -t 3dprinting993-simready:$(IMAGE_TAG) .

container-simready-workflow:
	docker build --platform linux/amd64 -f containers/simready-workflow.Dockerfile -t 3dprinting993-simready-workflow:$(IMAGE_TAG) .

container-simready-local-ai:
	docker build --platform linux/amd64 -f containers/simready-local-ai.Dockerfile -t 3dprinting993-simready-local-ai:$(IMAGE_TAG) .

container-smoke:
	docker run --rm 3dprinting993-recon:$(IMAGE_TAG) smoke-test.sh recon
	docker run --rm 3dprinting993-cadsim:$(IMAGE_TAG) smoke-test.sh cadsim
	docker run --rm 3dprinting993-mesh-cfd:$(IMAGE_TAG) smoke-test.sh mesh-cfd

container-push-mesh-cfd:
	docker tag 3dprinting993-mesh-cfd:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)

container-smoke-physicsml:
	docker run --rm 3dprinting993-physicsml:$(IMAGE_TAG) smoke-test.sh physicsml

container-smoke-simready:
	docker run --rm --platform linux/amd64 3dprinting993-simready:$(IMAGE_TAG) smoke-test.sh simready

container-smoke-simready-workflow:
	docker run --rm --platform linux/amd64 3dprinting993-simready-workflow:$(IMAGE_TAG) smoke-test.sh simready-workflow

container-smoke-simready-local-ai:
	docker run --rm --platform linux/amd64 3dprinting993-simready-local-ai:$(IMAGE_TAG) smoke-test.sh simready-local-ai

container-smoke-all: container-smoke container-smoke-physicsml container-smoke-simready container-smoke-simready-workflow

container-push-simready:
	docker tag 3dprinting993-simready:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-simready:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-simready:$(IMAGE_TAG)

container-push-simready-workflow:
	docker tag 3dprinting993-simready-workflow:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-simready-workflow:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-simready-workflow:$(IMAGE_TAG)

container-push-simready-local-ai:
	docker tag 3dprinting993-simready-local-ai:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-simready-local-ai:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-simready-local-ai:$(IMAGE_TAG)

container-push:
	docker tag 3dprinting993-recon:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker tag 3dprinting993-cadsim:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker tag 3dprinting993-physicsml:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
