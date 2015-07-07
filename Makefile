PYTHON?=python3

build: src/__init__.py src/transformers.py src/tracing.py
	${PYTHON} setup.py build

install: build
	${PYTHON} setup.py install
