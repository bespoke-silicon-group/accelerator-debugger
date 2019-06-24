PYPY := 1
ifdef PYPY
    PYTHON := pypy
else
    PYTHON := python3
endif

DATA := data/fft_good.vcd
BINARY := data/fft_good

all:
	$(PYTHON) debugger.py $(DATA) manycore
regen:
	$(PYTHON) debugger.py --regen $(DATA) manycore
test:
	$(PYTHON) debugger.py data/ex.vcd test
siglist:
	$(PYTHON) debugger.py $(DATA) manycore --dump-siglist data/splitpacked.siglist

elftest:
	$(PYTHON) elftest.py $(BINARY)
