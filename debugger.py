#! /usr/bin/env python3

# Eventually, assign HW modules to panels, update panels in parallel

import argparse
from lib.vcd_parser import VCDData
from lib.runtime import Runtime
from test_model import TestModel
from manycore_model import ManycoreModel


def main():
    """Run the debugger"""
    parser = argparse.ArgumentParser(description='VCD Trace Debugger')
    parser.add_argument("INPUT", type=str,
                        help="Input VCD file")

    args = parser.parse_args()

    model = ManycoreModel()

    vcd = VCDData(args.INPUT, siglist=model.get_signal_names())
    model.set_data(vcd)

    runtime = Runtime(None, model)
    runtime.start()


if __name__ == "__main__":
    main()
