.PHONY: check validate test twin twin-validate turbo-cold-side turbo-cold-side-check turbo-variants turbo-variants-check turbo-dyno turbo-dyno-check container-recon container-cadsim container-mesh-cfd container-physicsml container-smoke container-smoke-physicsml container-smoke-all container-push container-push-mesh-cfd

REGISTRY ?= ghcr.io/cluster2600
IMAGE_TAG ?= dev
PHYSICSNEMO_EXTRAS ?= cu12,sym,mesh-extras,model-extras

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

test:
	python3 -m unittest discover -s tests -v

twin:
	python3 scripts/twin_coverage.py

twin-validate:
	python3 scripts/validate_twin.py

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

container-smoke:
	docker run --rm 3dprinting993-recon:$(IMAGE_TAG) smoke-test.sh recon
	docker run --rm 3dprinting993-cadsim:$(IMAGE_TAG) smoke-test.sh cadsim
	docker run --rm 3dprinting993-mesh-cfd:$(IMAGE_TAG) smoke-test.sh mesh-cfd

container-push-mesh-cfd:
	docker tag 3dprinting993-mesh-cfd:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)

container-smoke-physicsml:
	docker run --rm 3dprinting993-physicsml:$(IMAGE_TAG) smoke-test.sh physicsml

container-smoke-all: container-smoke container-smoke-physicsml

container-push:
	docker tag 3dprinting993-recon:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker tag 3dprinting993-cadsim:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker tag 3dprinting993-physicsml:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-physicsml:$(IMAGE_TAG)
