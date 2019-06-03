PYPY := pypy
ifdef PYPY
    PYTHON := $(PYPY)
else
    PYTHON := python3
endif

# all:
	# pipenv run $(PYTHON) debugger.py data/vcd.vcd manycore
all:
	$(PYTHON) debugger.py data/vcd.vcd manycore
test:
	pipenv run $(PYTHON) debugger.py data/ex.vcd test
