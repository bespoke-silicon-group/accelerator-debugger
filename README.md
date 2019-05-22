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
* Currently fails because signal values are strings instead of numbers

### TODO
[ ] Care about end time of simulation
[ ] `clear` command to clear output from last command
[ ] Implement breakpoints
    [ ] Breakpoint on "arbitrary boolean expression" (assign number)
        [ ] "Arbitrary boolean expression"; could eval(), maybe something
            faster?
    [ ] list breakpoints command (prints number, expression)
    [ ] Remove breakpoint command (takes number)
    [ ] run <time> (run execution forward until <time>)
[ ] Minor refactor with @property
[ ] Reverse Execution
    [ ] rstep (default 1, takes n)
    [ ] go <time> (go to specified time)
[ ] Always show simulation time to right of command bar (as rprompt)
[ ] When instantiating module, SW dev can decide what signals to include
   (by default, includes all)
[ ] Display information as densely as possible (Micheal, Mark disagrees)

### Stretch
[ ] We could write the cached database created from VPD into a file; loader
    checks if JSON or VPD format and either runs `parse_vpd()` or just loads.
    Add a command line --regen option to force running `parse_vpd()`
[ ] Hook into ELF file stubs (there's a GNU library for this)
