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
This project uses [pipenv](https://pipenv.readthedocs.io/en/latest/) to manage
packages. Pipenv can be installed via:
`pip install --user pipenv` or `brew install pipenv`.

After pipenv is installed, packages can be installed with:
`pipenv install`

The project can be run with:
`pipenv run python <python_file>`


## Getting Started
For ease of compatibility, we only support VCD (value change dump) files,
instead of Synopsys's proprietary VPD file format. To convert between VPD files
and VCD files, Synopsys provides a tool with a standard VCS installation:
`vpd2vcd <input_vpd_file> <output_vcd_file>`

By default, `vpd2vcd` doesn't unpack structures, which can make debugging
challenging in projects that make heavy use of packed structures. To generate
the unpacked VCD file, use the `+splitpacked` flag when running `vpd2vcd`.

Compared to VPD files, VCD files can be extremely large (on the order of 4GB
for a VCD file that was generated from a 50MB VPD file). One way of reducing
the size of the resulting VCD file is to only translate value changes within a
certain time range. This can be accomplished with the following:
`vpd2vcd +start+<start_time> +end+<end_time> <input_file> <output_file>`

## Creating a DebugModel
To use the debugger, one needs to create a `DebugModel` based on the hardware
used. See `test_model.py` for a simple version of a `DebugModel` and
`manycore_model.py` for a more complex version. A `DebugModel` is a series of
`DebugModule` that, in turn, are a collection of signals. To create a `DebugModel`,
one needs to determine which signals in the VCD are useful for debugging, then
wrap those signals into logical `DebugModule` units.

Currently, there are two types of `DebugModule` units. A `BasicModule` is just a
wrapper for signals and is instantiated by providing a name for the module and
a list of signals names that the module composes. A `Memory` takes address,
write data, and write enable signal names, as well as the assertion level of
the write enable as a boolean. Additionally, one can select segments of the of
the memory that are of interest by providing a list of segments when
initializing the `Memory`.

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

### Stretch things to add
[ ] Hook into ELF file stubs (there's a GNU library for this)
[ ] When instantiating module, SW dev can decide what signals to include
   (by default, includes all)
[ ] Parse AST to see what vars breakpoints depends on
