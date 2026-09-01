.PHONY: check validate test twin twin-validate engine-contracts engine-components engine-contracts-check valve-variants omniverse-assembly turbo-cold-side turbo-cold-side-check turbo-variants turbo-variants-check turbo-dyno turbo-dyno-check container-recon container-cadsim container-mesh-cfd container-physicsml container-simready container-smoke container-smoke-physicsml container-smoke-simready container-smoke-all container-push container-push-mesh-cfd container-push-simready

REGISTRY ?= ghcr.io/cluster2600
IMAGE_TAG ?= dev
PHYSICSNEMO_EXTRAS ?= cu12,sym,mesh-extras,model-extras
VALVE_IMAGE ?= ghcr.io/cluster2600/3dprinting993-mesh-cfd@sha256:a1db60cbf61bbcca52c171e50cab01ed0b6ec860b227e7c5fc50f7b809659b4f

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

container-smoke-all: container-smoke container-smoke-physicsml container-smoke-simready

container-push-simready:
	docker tag 3dprinting993-simready:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-simready:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-simready:$(IMAGE_TAG)

container-push:
	docker tag 3dprinting993-recon:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker tag 3dprinting993-cadsim:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker tag 3dprinting993-physicsml:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
