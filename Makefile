.PHONY: check validate test container-recon container-cadsim container-mesh-cfd container-smoke container-push container-push-mesh-cfd

REGISTRY ?= ghcr.io/cluster2600
IMAGE_TAG ?= dev

check: validate test

validate:
	python3 scripts/validate_catalog.py
	python3 scripts/validate_sources.py
	python3 scripts/validate_measurements.py
	python3 scripts/validate_specifications.py
	python3 scripts/validate_twins.py
	python3 scripts/validate_components.py

test:
	python3 -m unittest discover -s tests -v

container-recon:
	docker build -f containers/recon.Dockerfile -t 3dprinting993-recon:$(IMAGE_TAG) .

container-cadsim:
	docker build -f containers/cadsim.Dockerfile -t 3dprinting993-cadsim:$(IMAGE_TAG) .

container-mesh-cfd:
	docker build -f containers/mesh-cfd.Dockerfile -t 3dprinting993-mesh-cfd:$(IMAGE_TAG) .

container-smoke:
	docker run --rm 3dprinting993-recon:$(IMAGE_TAG) smoke-test.sh recon
	docker run --rm 3dprinting993-cadsim:$(IMAGE_TAG) smoke-test.sh cadsim
	docker run --rm 3dprinting993-mesh-cfd:$(IMAGE_TAG) smoke-test.sh mesh-cfd

container-push-mesh-cfd:
	docker tag 3dprinting993-mesh-cfd:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-mesh-cfd:$(IMAGE_TAG)

container-push:
	docker tag 3dprinting993-recon:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker tag 3dprinting993-cadsim:$(IMAGE_TAG) $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-recon:$(IMAGE_TAG)
	docker push $(REGISTRY)/3dprinting993-cadsim:$(IMAGE_TAG)
