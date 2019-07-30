PYPY := 1
ifdef PYPY
    PYTHON := pypy
else
    PYTHON := python3
endif

DATA := data/fft_fail.vcd
BINARY := data/fft_fail

all:
	$(PYTHON) debugger.py $(DATA) manycore --binary $(BINARY)
regen:
	$(PYTHON) debugger.py --regen $(DATA) manycore --binary $(BINARY)
test:
	$(PYTHON) debugger.py data/ex.vcd test
siglist:
	$(PYTHON) debugger.py $(DATA) manycore --dump-siglist data/splitpacked.siglist
