#! /usr/bin/env python3

# Eventually, assign HW modules to panels, update panels in parallel

import argparse
from lib.vcd_parser import VCDData
from lib.runtime import Runtime
from test_model import TestModel, TestView
from manycore_model import ManycoreModel, ManycoreView


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

    args = parser.parse_args()

    if args.MODEL.lower() == 'test':
        model = TestModel()
        display = TestView(model)
    elif args.MODEL.lower() == 'manycore':
        model = ManycoreModel()
        display = ManycoreView(model)

    vcd = VCDData(args.INPUT, siglist=model.get_signal_names(),
                  cached=True, regen=args.regen,
                  siglist_dump_file=args.siglist_dump_file)
    model.set_data(vcd)

    runtime = Runtime(display, model)
    runtime.start()


if __name__ == "__main__":
    main()
