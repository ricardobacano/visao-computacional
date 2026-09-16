PYTHON := .venv/bin/python
PIP := .venv/bin/pip
CAMERA_SOURCE ?= 0

.PHONY: setup check capture calibrate undistort project pipeline

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	cp --update=none config.example.json config.json || true

check:
	$(PYTHON) -m compileall -q src

capture:
	CAMERA_SOURCE='$(CAMERA_SOURCE)' $(PYTHON) src/capture.py --config config.json

calibrate:
	$(PYTHON) src/calibrate.py --config config.json

undistort:
	$(PYTHON) src/undistort.py

project:
	$(PYTHON) src/project_points.py --config config.json

pipeline:
	$(PYTHON) src/run_pipeline.py --config config.json
