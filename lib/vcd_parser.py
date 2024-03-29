"""
This is a manual translation, from perl to python, of:
 http://cpansearch.perl.org/src/GSULLIVAN/Verilog-VCD-0.03/lib/Verilog/VCD.pm
With some adaptations added after the fact.
"""

import re
import os.path
import json
import lzma
from collections import namedtuple


class VCDParseError(Exception):
    """our local exception for VCD parsing errors (inherited from Exception)"""


class VCDData():
    """Class to act as a container, parser, and cache"""
    def __init__(self, filename, siglist=None, cached=False, regen=False,
                 siglist_dump_file=None):
        self.timescale = None
        self.change = namedtuple("Change", "time val")
        if siglist_dump_file is not None:
            self.dump_signal_list(filename, siglist_dump_file)
            exit(0)

        self.check_signals(filename, siglist)

        if cached:
            cached_fname = filename + ".cached"
            if os.path.isfile(cached_fname) and not regen:
                # Load cache file instead of reading vcd data
                print("Cached data found, loading")
                with open(cached_fname, "r") as cfile:
                    cache_dict = json.load(cfile)
                    self.vcd = cache_dict['vcd']
                    self.timescale = cache_dict['timescale']
                    self.endtime = cache_dict['endtime']
            else:
                print("Regenerating cached data")
                self._parse_vcd(filename, only_sigs=False,
                                siglist=siglist, opt_timescale='')
                cache_dict = {'vcd': self.vcd,
                              'endtime': self.endtime,
                              'timescale': self.timescale}
                with open(cached_fname, 'w+') as cfile:
                    json.dump(cache_dict, cfile)
                print("Data generated and cached!")
        else:
            self._parse_vcd(filename, only_sigs=False,
                            siglist=siglist, opt_timescale='')
        self.mapping = {}
        for k in self.vcd.keys():
            signal = self.vcd[k]
            nets = signal['nets']
            for net in nets:
                net_name = net['name']
                self.mapping[net['hier']+'.'+net_name] = k

    def get_value(self, sig, time):
        """Gets the value of sig at the given time"""
        # This could be sped up by saving a pointer to the last time
        # but we'd need to change some things so that rsteps still worked
        signal = self.vcd[sig.symbol]
        curr_value = None
        value_time = -1
        for (tv_time, tv_val) in signal['tv']:
            if value_time < tv_time <= time:
                curr_value = tv_val
            elif time < tv_time:
                break
        return curr_value

    def get_next_change(self, sig, curr_time):
        """Returns a (time, value) tuple that describes the next change for
        sig after curr_time. Returns None if a next change doesn't exist"""
        signal = self.vcd[sig.symbol]
        for (tv_time, tv_val) in signal['tv']:
            if tv_time > curr_time:
                return self.change(tv_time, tv_val)
        return None

    def get_prev_change(self, sig, curr_time):
        """Returns a (time, value) tuple that describes the previous change for
        sig before curr_time. Returns None if a change doesn't exist"""
        signal = self.vcd[sig.symbol]
        curr_value = None
        value_time = -1
        for (tv_time, tv_val) in signal['tv']:
            if tv_time < curr_time:
                curr_value, value_time = tv_val, tv_time
            elif tv_time >= curr_time:
                return self.change(value_time, curr_value)
        return None

    def get_symbol(self, sig_name):
        """Gets the VCD symbol associated with sig_name"""
        return self.mapping[sig_name]

    def dump_signal_list(self, file, dump_file):
        """Dumps list of all signals in <file> into <dump_file>"""
        self._parse_vcd(file, only_sigs=1)
        with open(dump_file, 'w+') as dump_f:
            for symbol in self.vcd:
                heir = self.vcd[symbol]['nets'][0]['hier']
                name = self.vcd[symbol]['nets'][0]['name']
                dump_f.write(f"{heir}.{name}\n")

    def check_signals(self, file, signals):
        """Parse VCD input file and make sure that all signals exist"""
        self._parse_vcd(file, siglist=signals, only_sigs=1)
        if len(self.vcd.keys()) != len(signals):
            key_signals = []
            for symbol in self.vcd:
                heir = self.vcd[symbol]['nets'][0]['hier']
                name = self.vcd[symbol]['nets'][0]['name']
                key_signals.append(f"{heir}.{name}")
            model_signals = signals.copy()
            for signal in signals:
                if signal in key_signals:
                    model_signals.remove(signal)
            print("\nDidn't find following signals")
            for signal in model_signals:
                print(signal)
            raise ValueError("Not all signals found")

    def _parse_var(self, line, hier, usigs, all_sigs):
        """ Parse a $var statement"""
        # assumes all on one line:
        #   $var reg 1 *@ data $end
        #   $var wire 4 ) addr [3:0] $end
        line_split = line.split()
        (sig_type, size, code) = line_split[1:4]
        name = "".join(line_split[4:-1]).split('[')[0]
        path = '.'.join(hier)
        full_name = path + '.' + name
        if (full_name in usigs) or all_sigs:
            if code not in self.vcd:
                self.vcd[code] = {}
            if 'nets' not in self.vcd[code]:
                self.vcd[code]['nets'] = []
            var_struct = {
                'type': sig_type,
                'name': name,
                'size': size,
                'hier': path,
            }
            if var_struct not in self.vcd[code]['nets']:
                self.vcd[code]['nets'].append(var_struct)

    def _parse_change(self, line, time):
        """Parse a change of value in the VCD. Return True if parse was
        successful, false otherwise"""
        if line[0] in ('b', 'B', 'r', 'R'):
            (value, code) = line[1:].split()
            if code in self.vcd:
                if 'tv' not in self.vcd[code]:
                    self.vcd[code]['tv'] = []
                self.vcd[code]['tv'].append((time, value))
            return True

        if line[0] in ('0', '1', 'x', 'X', 'z', 'Z'):
            value = line[0]
            code = line[1:]
            if code in self.vcd:
                if 'tv' not in self.vcd[code]:
                    self.vcd[code]['tv'] = []
                self.vcd[code]['tv'].append((time, value))
            return True
        return False

    def _parse_timescale(self, line, handle, opt_timescale, compressed):
        statement = line
        if "$end" not in line:
            while handle:
                if compressed:
                    line = handle.readline().decode('ascii')
                else:
                    line = handle.readline()
                statement += line
                if "$end" in line:
                    break

        return self._calc_mult(statement, opt_timescale)

    def _parse_enddefs(self, all_sigs):
        num_sigs = len(self.vcd)
        if not num_sigs and all_sigs:
            VCDParseError("Error: No signals found. Check the file"
                          "for proper var syntax.")

        elif not num_sigs:
            VCDParseError("Error: No matching signals found."
                          " Use list_sigs"
                          " to view all signals in the VCD file.")

    def _parse_vcd(self, file, only_sigs=0, siglist=None, opt_timescale=''):
        """Parse input VCD file into data structure.
        Also, print t-v pairs to STDOUT, if requested."""

        usigs = dict(zip(siglist, [1]*len(siglist))) if siglist else {}
        all_sigs = not bool(usigs)

        self.vcd = {}
        mult = 0
        hier = []
        time = 0
        compressed = False

        if file.endswith('.xz'):
            compressed = True
            file_handle = lzma.open(file)
        else:
            file_handle = open(file, 'r')

        while True:
            if compressed:
                line = file_handle.readline().decode('ascii')
            else:
                line = file_handle.readline()
            if line == '':  # EOF
                break

            line = line.strip()

            # if nothing left after we strip whitespace, go to next line
            if line == '':
                continue

            # put most frequent lines encountered at start of case,
            # so other clauses usually don't need to be tested
            if self._parse_change(line, time):
                continue

            elif line[0] == '#':
                time = mult * int(line[1:])
                self.endtime = time

            elif "$enddefinitions" in line:
                self._parse_enddefs(all_sigs)
                if only_sigs:
                    break

            elif "$timescale" in line:
                mult = self._parse_timescale(line, file_handle, opt_timescale,
                                             compressed)

            elif "$scope" in line:
                # assumes all on one line
                #   $scope module dff end
                hier.append(line.split()[2])  # just keep scope name

            elif "$upscope" in line:
                hier.pop()

            elif "$var" in line:
                self._parse_var(line, hier, usigs, all_sigs)

        # If any signals were never toggled, set them to 'x' at t=0
        for code in self.vcd:
            if 'tv' not in self.vcd[code]:
                self.vcd[code]['tv'] = [(0, 'x')]

    def _calc_mult(self, statement, opt_timescale=''):
        """
        Calculate a new multiplier for time values.
        Input statement is complete timescale, for example:
        timescale 10ns end
        Input new_units is one of s|ms|us|ns|ps|fs.
        Return numeric multiplier.
        Also sets the package timescale variable.
        """

        fields = statement.split()
        fields.pop()   # delete end from array
        fields.pop(0)  # delete timescale from array
        tscale = ''.join(fields)

        new_units = ''
        if opt_timescale != '':
            new_units = opt_timescale.lower()
            new_units = re.sub(r"\s", '', new_units)
            self.timescale = "1"+new_units

        else:
            self.timescale = tscale
            return 1

        mult = 0
        units = 0
        ts_match = re.match(r"(\d+)([a-z]+)", tscale)
        if ts_match:
            mult = int(ts_match.group(1))
            units = ts_match.group(2).lower()

        else:
            VCDParseError("Error: Unsupported timescale found in VCD "
                          "file: "+tscale+".  Refer to the Verilog LRM.")

        mults = {
            'fs': 1e-15,
            'ps': 1e-12,
            'ns': 1e-09,
            'us': 1e-06,
            'ms': 1e-03,
            's': 1e-00,
        }
        mults_keys = mults.keys()
        mults_keys.sort(key=lambda x: mults[x])
        usage = '|'.join(mults_keys)

        scale = 0
        if units in mults:
            scale = mults[units]

        else:
            VCDParseError("Error: Unsupported timescale units found in VCD "
                          "file: "+units+".  Supported values are: "+usage)

        new_scale = 0
        if new_units in mults:
            new_scale = mults[new_units]

        else:
            VCDParseError("Error: Illegal user-supplied "
                          "timescale: "+new_units+".  Legal values are: " +
                          usage)

        return (mult * scale) / new_scale

    def get_timescale(self):
        """
        This returns a string corresponding to the timescale as specified
        by the C<$timescale> VCD keyword.  It returns the timescale for
        the last VCD file parsed.  If called before a file is parsed, it
        returns an undefined value.  If the C<parse_vcd> C<timescale> option
        was used to specify a timescale, the specified value will be returned
        instead of what is in the VCD file.
        """
        return self.timescale

    def get_endtime(self):
        """ This returns the last time found in the VCD file, scaled
        appropriately.  It returns the last time for the last VCD file parsed.
        If called before a file is parsed, it returns an undefined value.
        """
        return self.endtime

# =head1 NAME
#
# Verilog_VCD - Parse a Verilog VCD text file
#
# =head1 VERSION
#
# This document refers to Verilog::VCD version 1.10.
#
# =head1 SYNOPSIS
#
#     from Verilog_VCD import parse_vcd
#     vcd = parse_vcd('/path/to/some.vcd')
#
# =head1 SUBROUTINES
#
# =head2 parse_vcd(file, $opt_ref)
#
# Parse a VCD file and return a reference to a data structure which
# includes hierarchical signal definitions and time-value data for all
# the specified signals.  A file name is required.  By default, all
# signals in the VCD file are included, and times are in units
# specified by the C<$timescale> VCD keyword.
#
#     vcd = parse_vcd('/path/to/some.vcd')
#
# It returns a reference to a nested data structure.  The top of the
# structure is a Hash-of-Hashes.  The keys to the top hash are the VCD
# identifier codes for each signal.  The following is an example
# representation of a very simple VCD file.  It shows one signal named
# C<chip.cpu.alu.clk>, whose VCD code is C<+>.  The time-value pairs
# are stored as an Array-of-Tuples, referenced by the C<tv> key.  The
# time is always the first number in the pair, and the times are stored in
# increasing order in the array.
#
#     {
#       '+' : {
#                'tv' : [
#                          (
#                            0,
#                            '1'
#                          ),
#                          (
#                            12,
#                            '0'
#                          ),
#                        ],
#                'nets' : [
#                            {
#                              'hier' : 'chip.cpu.alu.',
#                              'name' : 'clk',
#                              'type' : 'reg',
#                              'size' : '1'
#                            }
#                          ]
#              }
#     }
#
# Since each code could have multiple hierarchical signal names, the names are
# stored as an Array-of-Hashes, referenced by the C<nets> key.  The example
# above only shows one signal name for the code.
#
#
# =head3 OPTIONS
#
# Options to C<parse_vcd> should be passed as a hash reference.
#
# =over 4
#
# =item timescale
#
# It is possible to scale all times in the VCD file to a desired timescale.
# To specify a certain timescale, such as nanoseconds:
#
#     vcd = parse_vcd(file, opt_timescale='ns'})
#
# Valid timescales are:
#
#     s ms us ns ps fs
#
# =item siglist
#
# If only a subset of the signals included in the VCD file are needed,
# they can be specified by a signal list passed as an array reference.
# The signals should be full hierarchical paths separated by the dot
# character.  For example:
#
#     signals = [
#         'top.chip.clk',
#         'top.chip.cpu.alu.status',
#         'top.chip.cpu.alu.sum[15:0]',
#     ]
#     vcd = parse_vcd(file, siglist=signals)
#
# Limiting the number of signals can substantially reduce memory usage of the
# returned data structure because only the time-value data for the selected
# signals is loaded into the data structure.
#
# =item only_sigs
#
# Parse a VCD file and return a reference to a data structure which
# includes only the hierarchical signal definitions.  Parsing stops once
# all signals have been found.  Therefore, no time-value data are
# included in the returned data structure.  This is useful for
# analyzing signals and hierarchies.
#
#     vcd = parse_vcd(file, only_sigs=1)
#
# =back
#
#
# =head2 list_sigs(file)
#
# Parse a VCD file and return a list of all signals in the VCD file.
# Parsing stops once all signals have been found.  This is
# helpful for deciding how to limit what signals are parsed.
#
# Here is an example:
#
#     signals = list_sigs('input.vcd')
#
# The signals are full hierarchical paths separated by the dot character
#
#     top.chip.cpu.alu.status
#     top.chip.cpu.alu.sum[15:0]
#
# =head1 LIMITATIONS
#
# Only the following VCD keywords are parsed:
#
#     $end                $scope
#     $enddefinitions     $upscope
#     $timescale          $var
#
# The extended VCD format (with strength information) is not supported.
#
# The default mode of C<parse_vcd> is to load the entire VCD file into the
# data structure.  This could be a problem for huge VCD files.  The best
# solution to any memory problem is to plan ahead and keep VCD files as small
# as possible.
# When simulating, dump fewer signals and scopes, and use shorter dumping
# time ranges.  Another technique is to parse only a small list of signals
# using the C<siglist> option; this method only loads the desired signals into
# the data structure.  Finally, the C<use_stdout> option will parse the input
# VCD file line-by-line, instead of loading it into the data structure, and
# directly prints time-value data to STDOUT.  The drawback is that this only
# applies to one signal.
#
# =head1 AUTHOR
#
# Originally written in Perl by Gene Sullivan (gsullivan@cpan.org)
# Translated into Python by Sameer Gauria (sgauria+python@gmail.com)
#
# Plus the following patches :
#  - Scott Chin : Handle upper-case values in VCD file.
#  - Sylvain Guilley : Fixed bugs in list_sigs.
#  - Bogdan Tabacaru : Fix bugs in globalness of timescale and endtime
#  - Andrew Becker : Fix bug in list_sigs
#  - Pablo Madoery : Found bugs in siglist and opt_timescale features.
#  - Matthew Clapp itsayellow+dev@gmail.com : Performance speedup, Exception,
#    print, open, etc cleanup to make the code more robust.
# Thanks!
#
# =head1 COPYRIGHT AND LICENSE
#
# Copyright (c) 2012 Gene Sullivan, Sameer Gauria.  All rights reserved.
#
# This module is free software; you can redistribute it and/or modify
# it under the same terms as Perl itself.  See L<perlartistic|perlartistic>.
#
# =cut
