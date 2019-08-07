"""Utilities for parsing ELF DWARF info and getting lines of source code that
correspond to addresses in the ELF binary"""

import subprocess
from elftools.common.py3compat import bytes2str
from elftools.dwarf.descriptions import describe_form_class
from elftools.elf.elffile import ELFFile
from elftools.elf.constants import SH_FLAGS
import lib.runtime


def _spike_dasm(instructions):
    # Use spike-dasm to disassemble machine opcodes to instructions
    dasm_arg = ""
    for inst in instructions:
        dasm_arg += f"DASM({inst})\n"
    try:
        spike_dasm = subprocess.Popen(('echo', dasm_arg),
                                      stdout=subprocess.PIPE)
        asm = subprocess.check_output(('spike-dasm'),
                                      stdin=spike_dasm.stdout)
        spike_dasm.wait()
    except:  # Something went wrong running spike-dasm
        return []
    return asm.strip().decode('ascii').split('\n')


def _get_instructions(elffile, elf_section, section_offset, num_lines):
    # Parse the ELF section for machine opcodes at 'address'
    data = elf_section.data()
    wsize = elffile.elfclass // 8  # Bytes per word
    inst_data = [data[i:i+wsize] for i in range(0, len(data), wsize)]
    if elffile.little_endian:
        inst_data = [inst[::-1] for inst in inst_data]  # Reverse insts
    for i, inst in enumerate(inst_data):
        inst_data[i] = [f"{hex(inst[i])[2:].zfill(2)}" for i in range(wsize)]
        inst_data[i] = "".join(inst_data[i])
    inst_offset = section_offset // wsize
    half_lines = num_lines // 2
    return inst_data[inst_offset-half_lines:inst_offset+half_lines+1]


def get_asm(filename, address, num_lines):
    """Get the assembly instructions associated with an address"""
    with open(filename, 'rb') as elffile:
        elffile = ELFFile(elffile)
        addr_section = None
        for section in elffile.iter_sections():
            section_start = section['sh_addr']
            section_end = section_start + section['sh_size']
            if section['sh_flags'] & SH_FLAGS.SHF_EXECINSTR:
                if section_start < address < section_end:
                    addr_section = section
        section_offset = address - addr_section['sh_addr']

        insts = _get_instructions(elffile, addr_section,
                                  section_offset, num_lines)
        return _spike_dasm(insts)


def _get_loc(filename, address):
    """Helper for doing address->source code translation"""
    with open(filename, 'rb') as elffile:
        elffile = ELFFile(elffile)

        if not elffile.has_dwarf_info():
            raise lib.runtime.InputException('file has no DWARF info')

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        func = decode_funcname(dwarfinfo, address)
        path, file, lineno = decode_file_line(dwarfinfo, address)
        if path is None:
            err = "Source lines for address not found"
            err += ", did you compile your binary with -g?"
            raise lib.runtime.InputException(err)

        return path, file, lineno, func


def get_source_loc(filename, address):
    """ Get the path and source line that corresponds to the given address"""
    path, file, lineno, _ = _get_loc(filename, address)
    full_path = path + "/" + file
    return full_path, lineno


def _get_source_text(path, file, func, addr, lineno, num_lines):
    """ Get multiple of lines of source around path/file:lineno"""
    out_text = [f"{hex(addr)} in {func}(), {file}:{lineno}"]
    # arrow = "\x1b[7;30;46m" + "<----" + "\x1b[0m"
    arrow = "<--"
    start_line = lineno - (num_lines // 2) - 2
    end_line = lineno + (num_lines // 2) - 1
    full_path = path + "/" + file
    with open(full_path) as bin_file:
        for i, line in enumerate(bin_file):
            if i in range(start_line, end_line):
                if i == lineno - 1:
                    out_text.append(f"{line[:-1]} {arrow}")
                else:
                    out_text.append(f"{line[:-1]}")
            if i >= end_line:
                break
    return out_text


def get_source_lines(filename, address, num_lines):
    """Try to get the source code line that's associated with a given address
    in a given ELF file"""
    path, file, lineno, func = _get_loc(filename, address)
    return _get_source_text(path, file, func, address, lineno, num_lines)


def decode_funcname(dwarfinfo, address):
    """Go over all DIEs in the DWARF information, looking for a subprogram
    entry with an address range that includes the given address. Note that
    this simplifies things by disregarding subprograms that may have
    split address ranges."""
    for compile_unit in dwarfinfo.iter_CUs():
        for DIE in compile_unit.iter_DIEs():
            try:
                if DIE.tag == 'DW_TAG_subprogram':
                    lowpc = DIE.attributes['DW_AT_low_pc'].value

                    # DWARF v4 in section 2.17 describes how to interpret the
                    # DW_AT_high_pc attribute based on the class of its form.
                    # For class 'address' it's taken as an absolute address
                    # (similarly to DW_AT_low_pc); for class 'constant', it's
                    # an offset from DW_AT_low_pc.
                    highpc_attr = DIE.attributes['DW_AT_high_pc']
                    highpc_attr_class = describe_form_class(highpc_attr.form)
                    if highpc_attr_class == 'address':
                        highpc = highpc_attr.value
                    elif highpc_attr_class == 'constant':
                        highpc = lowpc + highpc_attr.value
                    else:
                        print('Error: invalid DW_AT_high_pc class:',
                              highpc_attr_class)
                        continue

                    if lowpc <= address <= highpc:
                        return bytes2str(DIE.attributes['DW_AT_name'].value)
            except KeyError:
                continue
    return None


def decode_file_line(dwarfinfo, address):
    """Go over all the line programs in the DWARF information, looking for
       one that describes the given address."""
    for compile_unit in dwarfinfo.iter_CUs():
        # First, look at line programs to find the file/line for the address
        lineprog = dwarfinfo.line_program_for_CU(compile_unit)
        prevstate = None
        for entry in lineprog.get_entries():
            # We're interested in those entries where a new state is assigned
            if entry.state is None:
                continue
            if entry.state.end_sequence:
                # if the line number sequence ends, clear prevstate.
                prevstate = None
                continue
            # Looking for a range of addresses in two consecutive states that
            # contain the required address.
            entry_addr = entry.state.address
            if prevstate and prevstate.address <= address < entry_addr:
                filename = lineprog['file_entry'][prevstate.file - 1].name
                line = prevstate.line
                dir_num = lineprog['file_entry'][prevstate.file - 1].dir_index
                path = bytes2str(lineprog['include_directory'][dir_num - 1])
                return path, bytes2str(filename), line
            prevstate = entry.state
    return None, None, None

if __name__ == "__main__":
    print(get_asm('data/fft_good', 0xfd0, 5))
