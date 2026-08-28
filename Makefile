.PHONY: check validate test

check: validate test

validate:
	python3 scripts/validate_catalog.py
	python3 scripts/validate_sources.py

test:
	python3 -m unittest discover -s tests -v
