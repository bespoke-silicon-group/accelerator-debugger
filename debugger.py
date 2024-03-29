#! /usr/bin/env python3
""" Top-level file for the Visual Debugger, parses command line options and
    starts the display for a given model
"""

import argparse
from lib.vcd_parser import VCDData
from lib.runtime import Runtime
from models.test_model import TestModel, TestView
from models.manycore_model import ManycoreModel, ManycoreView
from models.blackparrot_model import BlackParrotModel, BlackParrotView


def main():
    """Run the debugger"""
    parser = argparse.ArgumentParser(description='VCD Trace Debugger')
    parser.add_argument('--regen', action='store_true', default=False,
                        help='Force regenting parsed VCD data')
    parser.add_argument('--dump-siglist', action='store',
                        dest='siglist_dump_file',
                        help='Dump the list of all signals out to a file')
    parser.add_argument("INPUT", type=str,
                        help="Input VCD file")
    parser.add_argument('MODEL', type=str,
                        help="Model for HW")
    parser.add_argument('--binary', action='store',
                        dest='bin_file', default=None,
                        help="ELF file used in simulation")
    parser.add_argument('--model-arg', action='append',
                        dest='model_args', default=[],
                        help="Arguments to pass to the model")

    args = parser.parse_args()

    if args.MODEL.lower() == 'test':
        model = TestModel(args.model_args)
        display = TestView(model)
    elif args.MODEL.lower() == 'manycore':
        model = ManycoreModel(args.model_args)
        display = ManycoreView(model)
    elif args.MODEL.lower() == 'blackparrot':
        model = BlackParrotModel(args.model_args)
        display = BlackParrotView(model)

    vcd = VCDData(args.INPUT, siglist=model.signal_names,
                  cached=True, regen=args.regen,
                  siglist_dump_file=args.siglist_dump_file)
    model.set_data(vcd)

    runtime = Runtime(display, model, args.bin_file)
    runtime.start()


if __name__ == "__main__":
    main()
