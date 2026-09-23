PYTHON := .venv/bin/python
PIP := .venv/bin/pip
.PHONY: setup check calibrate undistort project pipeline

setup:
	python3 -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	cp --update=none config.example.json config.json || true

check:
	$(PYTHON) -m compileall -q src

calibrate:
	$(PYTHON) src/calibrate.py --config config.json

undistort:
	$(PYTHON) src/undistort.py

project:
	$(PYTHON) src/project_points.py --config config.json

pipeline:
	$(PYTHON) src/run_pipeline.py --config config.json
