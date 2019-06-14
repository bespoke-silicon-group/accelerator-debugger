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

### Sim notes
 Stepping a simulation should just be stepping a HWModel, which
 steps all the module contained within it. Then, we can update
 each pane with the new information.

### Implementing Breakpoints
`break <condition>` where the condition is a blend of variables and operators
* Could implement with eval(), but language of condition needs to be python
    * This can be fix with a couple find-replaces
    * Can be sped up with `compiler.compile()`

### TODO
[ ] go <time> (go to specified time, ignoring breakpoints)
[ ] Refactor on lib/hw_models.py for pylint
[x] Always show simulation time to right of command bar (as rprompt)
[ ] Display information as densely as possible (Micheal, Mark disagrees)
    [ ] Align text on colon
    [ ] Standardized tab spacing
[ ] Speed up breakpoints with compiler.compile()

### Stretch
[ ] Hook into ELF file stubs (there's a GNU library for this)
[ ] When instantiating module, SW dev can decide what signals to include
   (by default, includes all)
[ ] Parse AST to see what vars breakpoints depends on

## Debugging The Manycore
* Register files (but maybe only some registers)
    * s7, s8 get loads; a0 holds store value, a1 holds address, a0/a1 hold
        addresses for loads (x10,x11, x23, x24)
    * Memory locations that are being loaded and stored on each core
        [0x1980-0x198c]
    * Maybe specifics on which cores are being addressed, but this is
     implicit in the address
* Loads at  0xba0, 0xba4
    * 00052b83 rd = 23, addr = r10
    * 0005ac03 rd = 24, addr = r11
* Stores at 0xc24, 0xc7c, 0xc90, 0xca4
    * 00a6a023, (data=r10, addr=r13)
    * 00a5a023, (data=r10, addr=r11)
    * 00a5a023, (data=r10, addr=r11)
    * 00a5a023, (data=r10, addr=r11)
* Remote loads and stores between cores
