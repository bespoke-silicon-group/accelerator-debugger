PYPY := pypy
ifdef PYPY
    PYTHON := $(PYPY)
else
    PYTHON := pipenv run python3
endif

DATA := data/splitpacked.vcd

all:
	$(PYTHON) debugger.py $(DATA) manycore
regen:
	$(PYTHON) debugger.py --regen $(DATA) manycore
test:
	$(PYTHON) debugger.py data/ex.vcd test
siglist:
	$(PYTHON) debugger.py $(DATA) manycore --dump-siglist data/splitpacked.siglist
