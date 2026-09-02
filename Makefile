.PHONY: check validate test twin twin-validate engine-contracts engine-components engine-contracts-check 917-complete-parts 917-complete-assembly 917-kinematics-f2 917-detail-f3 917-systems-f4 917-virtual-test-bench 917-test-bench-usd 917-start-support-f5 917-oil-prime-f6 917-motion-video-stages-f7 917-motion-video-render-f7 917-interfaces-f8-check 917-interfaces-f8-preflight 917-performance-envelope-f9 917-variant-geometry-f10-check 917-variant-geometry-f10 917-reengineering-f11 917-clean-sheet-head-f29 917-clean-sheet-head-f29-check 917-clean-sheet-head-f29-figures 917-head-reference-cae-f31-image 917-head-reference-cae-f31 917-head-reference-cae-f31-publish valve-variants omniverse-assembly turbo-cold-side turbo-cold-side-check turbo-variants turbo-variants-check turbo-dyno turbo-dyno-check container-recon container-cadsim container-mesh-cfd container-physicsml container-simready container-simready-workflow container-simready-local-ai container-smoke container-smoke-physicsml container-smoke-simready container-smoke-simready-workflow container-smoke-simready-local-ai container-smoke-all container-push container-push-mesh-cfd container-push-simready container-push-simready-workflow container-push-simready-local-ai

REGISTRY ?= ghcr.io/cluster2600
IMAGE_TAG ?= dev
PHYSICSNEMO_EXTRAS ?= cu12,sym,mesh-extras,model-extras
VALVE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f
CAD_AUTHOR_F29_IMAGE ?= ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
F31_CAE_IMAGE ?= 3dprinting993-cae-reference-f31:dev

check: validate test turbo-cold-side-check turbo-variants-check turbo-dyno-check

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
