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

### TODO
[ ] First run at panes
    [ ] Floating panel that shows text completion, positioned at cursor
        position (or just copy code from prompt)
    [ ] Panel class that takes a HW module

### Extra stretch
[ ] Implement breakpoints
[ ] Care about end time of simulation
[ ] Reverse Execution
