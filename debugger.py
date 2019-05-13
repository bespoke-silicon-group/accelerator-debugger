#! /usr/bin/env python3

import argparse
from vcd_parser import parse_vcd

parser = argparse.ArgumentParser(description='VCD Trace Debugger')
parser.add_argument("INPUT", type=str,
                    help="Input VCD file");

args = parser.parse_args()

vcd_data = parse_vcd(args.INPUT)
print(vcd_data)
