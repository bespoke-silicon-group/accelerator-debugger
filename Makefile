all:
	pipenv run python3 debugger.py data/vcd.vcd manycore
test:
	pipenv run python3 debugger.py data/ex.vcd test
