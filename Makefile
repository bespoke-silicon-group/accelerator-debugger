#PYPY := pypy
ifdef PYPY
    PYTHON := $(PYPY)
else
    PYTHON := pipenv run python3
endif

#test data
#DATA := data/ex.vcd

#manycore data
#DATA := data/splitpacked.vcd

#hammerblade
DATA := ../data/hammerblade.vcd

MODEL := hammerblade

all:
	$(PYTHON) debugger.py $(DATA) $(MODEL)
regen:
	$(PYTHON) debugger.py --regen $(DATA) $(MODEL)
test:
	$(PYTHON) debugger.py data/ex.vcd test
siglist:
	$(PYTHON) debugger.py $(DATA) $(MODEL) --dump-siglist data/splitpacked.siglist
