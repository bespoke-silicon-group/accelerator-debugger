PYPY := 1
ifeq ($(PYPY), 1)
    PYTHON := pypy
else
    PYTHON := python3
endif

$(info Using Python: ${PYTHON})

DATA := data/fft_fail.vcd
BINARY := data/fft_fail
MODEL := manycore

all:
	$(PYTHON) debugger.py $(DATA) $(MODEL) --binary $(BINARY)
regen:
	$(PYTHON) debugger.py --regen $(DATA) $(MODEL) --binary $(BINARY)
test:
	$(PYTHON) debugger.py data/ex.vcd test
siglist:
	$(PYTHON) debugger.py $(DATA) $(MODEL) --dump-siglist data/splitpacked.siglist
