# Agile Unhardware

This tool looks to build a unified debugging interface between custom
bleeding-edge hardware and application level software. While traditional
debugging approaches (GDB, etc) may be appropriate for mature hardware
platforms, debugging software running on custom hardware often involves
a need for quick and efficient triage to determine if the bug lies in
hardware or software so it can be assigned to the right people. Specifically,
the traditional application ABI and ISA-level program state is usually not
enough to determine what exactly is going wrong from a software level, on the
other side, VCS's waveform viewer often has too much information, creating
a heavyweight experience for software developers.

We assume that software developers have a general knowledge of the custom
hardware's interworking and work closely with hardware developers.


## Setup
This project assumes a minimum Python version of 3.6.

This project has two dependencies, `prompt_toolkit` and `pyelftools`. Both can
be installed with `pip`:

`pip3 install prompt_toolkit`

`pip3 install pyelftools`


## Getting Started
For ease of compatibility, we only support VCD (value change dump) files,
instead of Synopsys's proprietary VPD file format. To convert between VPD files
and VCD files, Synopsys provides a tool with a standard VCS installation:

`vpd2vcd <input_vpd_file> <output_vcd_file>`

By default, `vpd2vcd` doesn't unpack structures, which can make debugging
challenging in projects that make heavy use of packed structures. To generate
the unpacked VCD file, use the `+splitpacked` option when running `vpd2vcd`.

Compared to VPD files, VCD files can be extremely large (on the order of 4GB
for a VCD file that was generated from a 50MB VPD file). One way of reducing
the size of the resulting VCD file is to only translate value changes within a
certain time range. This can be accomplished with the following:

`vpd2vcd +start+<start_time> +end+<end_time> <input_file> <output_file>`

## Creating a DebugModel
To use the debugger, one needs to create a `DebugModel` based on the hardware
used. See `test_model.py` for a simple version of a `DebugModel` and
`manycore_model.py` for a more complex version. A `DebugModel` is a collection of
`DebugModule`s that, in turn, are a collection of signals. To create a `DebugModel`,
one needs to determine which signals in the VCD are useful for debugging, then
wrap those signals into logical `DebugModule` units.

Currently, there are three types of `DebugModule` units.
- A `BasicModule` is a simple wrapper for signals and is instantiated by
  providing a name for the module and a list of signals names that the module
  composes.
- A `Memory` takes address, write data, and write enable signal names, as well
  as the assertion level of the write enable as a boolean. Additionally, one can
  select segments of the of the memory that are of interest by providing a list
  of segments when initializing the `Memory`. `Memory` modules are used for
  tracking signals inside memories -- register file SRAMs, Data Memory SRAMs,
  and others.
- A `Core` takes a signal name that denotes the program counter for the core,
  and a list of signals that should also be tracked by the module. `Core`
  modules are useful for tracking logical hardware cores.

After modules are initialized, they can be added to the `DebugModel` via
`self.add_module` in the `__init__` function of the `DebugModel`.

## Creating a Display
Creating a display is simple! One only needs to override the `gen_top_view`
function of the `Display` class to select the modules that need to be
displayed, describe the arrangement of modules with horizontal splits
(`HSplit`, where the first module is above the other) and vertical splits (`VSplit`,
where the first module is to the left of the other). Splits can be composed
with other splits to create complex views with relatively little effort. The
function `gen_top_view` should return the top level `View`, `HSplit`, or
`VSplit`.

## Using the Debugger
### The Basics
* `fedge <n>`: advance <n> clock edges
* `redge <n>`: reverse <n> clock edges
* `run <time>`: Run simulation until a breakpoint is hit or <time> is reached
* `break <condition>`: Set a breakpoint -- conditions are given in Python syntax
  (see below)
* `lsbrk`: List active breakpoints
* `delete <num>`: Delete a breakpoint
* `clear`: Clear the output window
* `help`: Print help text

### Using Breakpoints
Breakpoint conditions are given in Python syntax (i.e. `and` instead of `&&`,
`not` instead of `!`). Users can describe signals via Python attributes. For
instance, if one wanted to set a breakpoint for when signal `foo` inside
`DebugModule` `bar` was non-zero, the following syntax would suffice:

`break bar.foo != 0`

If one wanted to set a breakpoint for when register 8 in `DebugModule` `RF` was
equal to `0xcafebebe`, one could use the following:

`break RF[8] == 0xcafebebe`

Note that the debugger treats don't cares by the SystemVerilog definition -- if
a signal's current value is `x`, any equality check with the signal will
evaluate to True.

### More Advanced
* `jump <time>`: Jump to a given simulation time, ignoring breakpoints
* `step <core_or_sig> <n>`: Step forward <n> lines in source for the given Core
  module or signal
* `where <module>`: Give source listing of where a core's execution is
* `traceback`: Given a point in simulation where some traced signal is 'x', find
  the last point in simulation where no signals were 'x'. Since signals in
  `Memory` modules are set to 'x' by default, they are ignored for `traceback`.
  
As a note, to use `step` or `where` the `--binary` flag needs to be used. For
where to include assembly listings, `spike-dasm` needs to be on the $PATH.

### Stretch things to add
- [ ] When instantiating module, SW dev can decide what signals to include
     (by default, includes all)
