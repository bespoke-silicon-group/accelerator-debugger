#! /usr/bin/env python3
""" The front end of the application:
    * Parsing user input is done by the InputHandler
    * Text completion is done by the ModuleCompleter
    * Runtime initializes and runs the application
"""


import pdb

import os.path
import re
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.widgets import TextArea, SearchToolbar, Label
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.menus import CompletionsMenu
import prompt_toolkit.layout.containers as pt_containers
import lib.elf_parser
from lib.hw_models import Core

# We run lstrip and rstrip before matching against regex
COMMANDS = [
    ("fedge <n>", "Run simulation <n> clock edges forward (default=1)",
     r"^(f|fedge)\s*(\d*)$"),

    ("redge <n>", "Run simulation <n> clock edges backward (default=1)",
     r"^(r|redge)\s*(\d*)$"),

    ("step <Core_or_sig> <n>", "Step <n> source code lines forward (default=1)",
     r"^(s|step)\s+([.\w]+)\s*(\d*)$"),

    ("rstep <Core_or_sig> <n>", "Step <n> source code lines backward (default=1)",
     r"^(rs|rstep)\s+([.\w]+)\s*(\d*)$"),

    ("break <condition>", "Set a breakpoint for <condition> (python syntax)",
     r"^(b|break) (.*)$"),

    ("lsbrk", "List all active breakpoints",
     r"^(l|lsbrk)$"),

    ("delete <n>", "Delete breakpoint <n>",
     r"^(d|delete) (\d+)$"),

    ("run <time>", "Run simulation until <time>",
     r"^(run)\s*(\d*)$"),

    ("jump <time>", "Jump to a given time ignoring breakpoints",
     r"^(j|jump)\s*(\d+)$"),

    ("where <core> <n>", "Give the source location for a given Core DebugModule",
     r"^(w|where)\s+([\w|\.]+)\s*(\d*)$"),

    ("info <module>", "Give detailed information on a module",
     r"^(i|info)\s*(\w+)$"),

    ("clear", "Clear the output window",
     r"^(c|clear)$"),

    ("quit", "Quit the debugger (also C-c, C-d)",
     r"^(q|quit)$"),

    ("help", "Print this help text",
     r"^(h|help)$"),

    ("modules", "Print a list of modules in the model",
     r"^(m|modules)$"),

    ("traceback", "Run simulation backwards to the last point without any 'x'",
     r"^(traceback)$"),

    ("debugger", "Launch the PDB debugger (for tool debugging)",
     r"^(debugger)$")
]

class ModuleCompleter(Completer):
    """Text completion for user-input, including completion for module names"""
    def __init__(self, module_names):
        self.module_names = module_names
        self.meta_dict = {}

    def get_completions(self, document, _):
        """Given the document, yield a Completion based on what the user's
        typed"""
        words = []
        text = document.text.strip()
        typed = document.text.strip().split()
        num_words = len(typed)
        words = [command[0].split()[0] for command in COMMANDS]
        if (num_words > 1 and typed[0] == 'info') or (text == 'info'):
            words = self.module_names
        elif num_words == 1 and (typed[0] in COMMANDS or text in COMMANDS):
            words = []

        word_before_cursor = document.get_word_before_cursor(WORD=False)

        def word_matches(word):
            return word.startswith(word_before_cursor)

        for word in words:
            if word_matches(word):
                display_meta = self.meta_dict.get(word, '')
                yield Completion(word, -len(word_before_cursor),
                                 display_meta=display_meta)


class InputException(Exception):
    """Custom exception to throw when we find invalid user input"""


class InputHandler():
    """ Handle input from the user, throwing errors as necessary """
    def __init__(self, runtime, model, bin_file):
        self.runtime = runtime
        self.model = model
        self.bkpt_namespace = {}
        for module in self.model.modules:
            self.bkpt_namespace[module.name] = module.signal_dict
        self.breakpoints = []
        self.next_bkpt_num = 0
        self.last_text = []
        self.bin_file = bin_file

    def _check_breakpoints(self):
        for module in self.model.modules:
            self.bkpt_namespace[module.name] = module.signal_dict
        for num, _, cond in self.breakpoints:
            if eval(cond, {}, self.bkpt_namespace):
                return num
        return None

    def fedge(self, num_edges):
        """ Handle the 'fedge' command """
        if not num_edges:
            num_edges = '1'
        num_edges = int(num_edges)
        if self.breakpoints:
            while num_edges > 0:
                self.model.edge()
                sim_time = self.model.sim_time
                bkpt_num = self._check_breakpoints()
                if bkpt_num is not None:
                    return f"Hit breakpoint {bkpt_num} at time {sim_time}"
                if sim_time >= self.model.get_end_time():
                    return f"Hit simulation end at time {self.model.sim_time}"
                num_edges -= 1
                self.runtime.update_time()
            return ""
        self.model.update(num_edges)
        self.runtime.update_time()
        if self.model.sim_time >= self.model.get_end_time():
            return f"Hit end of simulation at time {self.model.sim_time}"
        return ""

    def redge(self, num_edges):
        """ Handle the 'redge' and 'r' commands -- reverse clock edge"""
        if not num_edges:
            num_edges = '1'
        num_edges = int(num_edges)
        self.model.rupdate(num_edges)
        self.runtime.update_time()
        return ""

    def module_info(self, module_name):
        """ Handle the 'info' command """
        modules = self.model.modules
        req_module = [m for m in modules if m.name == module_name]
        if not req_module:
            raise InputException("Module not found!")
        return f"{str(req_module[0])}\n"

    def breakpoint(self, condition):
        """ Handle the 'breakpoint' command """
        try:
            current_cond = eval(condition, {}, self.bkpt_namespace)
        except Exception as e:  # Bare except, since this is literally a catch-all
            raise InputException("Invalid breakpoint condition!\n" + str(e))
        if not isinstance(current_cond, bool):
            raise InputException("Breakpoint condition not boolean!")

        compiled_cond = compile(condition, '<string>', 'eval')
        bkpt_num = self.next_bkpt_num
        self.next_bkpt_num += 1
        self.breakpoints.append((bkpt_num, condition, compiled_cond))
        return f"Breakpoint {bkpt_num}: {condition}"

    def lsbrk(self):
        """ Handle the lsbrk command -- list breakpoints """
        out_text = ""
        for bkpt_num, condition, _ in self.breakpoints:
            out_text += f"Breakpoint {bkpt_num}: {condition}\n"
        return out_text[:-1]  # Strip final newline

    def delete(self, num):
        """ Handle the delete command -- delete breakpoint """
        bkpt_num = int(num)
        for i, bkpt in enumerate(self.breakpoints):
            if bkpt[0] == bkpt_num:
                self.breakpoints.pop(i)
                return f"Removed breakpoint {bkpt_num}"
        raise InputException(f"Breakpoint {bkpt_num} not found!")

    def run(self, end_time):
        """ Handle the run command -- forward execution to a given time """
        curr_time = self.model.sim_time
        if not end_time:
            end_time = str(self.model.end_time)
        end_time = int(end_time)
        if end_time < curr_time:
            raise InputException("Time must be later than current time")
        edges = (end_time - curr_time) // self.model.edge_time
        return self.fedge(edges)

    def jump(self, jump_time):
        """ Handle the go command -- jump to a given time"""
        dest_time = int(jump_time)
        curr_time = self.model.sim_time
        edges = abs(dest_time - curr_time) // self.model.edge_time
        if dest_time < curr_time:
            self.model.rupdate(edges)
        else:
            self.model.update(edges)
        return ""

    def list_modules(self):
        """ Handle the modules command -- list all modules """
        out_text = ""
        for module in self.model.modules:
            out_text += f"* {module.name}\n"
        return out_text

    def where(self, location, num_lines):
        """ Handle the `where` commmand: display source code that given core
        module is executing"""
        modules = self.model.modules
        address = None
        if not num_lines:
            num_lines = 5
        num_lines = int(num_lines)
        if self.bin_file is None:
            raise InputException("Need to run with --binary to use where!")
        try:  # treat location as an address
            address = int(location, 0)
        except ValueError:
            req_module = [m for m in modules if m.name == location]
            if req_module:  # Treat location as a Core module
                if not isinstance(req_module[0], Core):
                    raise InputException("where must be given a Core module")
                address = req_module[0].pc.value.as_int
            else:  # Treat location as a signal
                for module in self.model.modules:
                    self.bkpt_namespace[module.name] = module.signal_dict
                address = eval(location, {}, self.bkpt_namespace)
        if address is None:
            raise InputException("Core module has invalid address")
        source = lib.elf_parser.get_source_lines(self.bin_file, address,
                                                 num_lines)
        asm = lib.elf_parser.get_asm(self.bin_file, address, num_lines)
        out_text = source[0] + '\n\n'
        if asm:
            asm[num_lines // 2] += "  <--"
            for i, asm_line in enumerate(asm):
                out_text += f"{asm_line:<25}     |   {source[i+1]:>}\n"
        else:
            for i in range(1, len(source)):
                out_text += f"{source[i]:<}\n"
        return out_text

    def step(self, forward, location, num_steps):
        """ Handle the `step` and `rstep` commands -- move execution until the
        source line that corresponds to the core_module changes"""
        if not num_steps:
            num_steps = 1
        modules = self.model.modules
        req_module = [m for m in modules if m.name == location]
        is_module = False
        if req_module:  # Treat location as a Core module
            if not isinstance(req_module[0], Core):
                raise InputException("where must be given a Core module")
            addr = req_module[0].pc.value.as_int
            if addr is None:
                raise InputException("Core module has invalid address")
            is_module = True
        else:  # Treat Location as a signal
            self.bkpt_namespace = self.model.signal_dict
            try:
                addr = eval(location, {}, self.bkpt_namespace)
            except AttributeError:
                raise InputException("Invalid Location for step!")
        file, line = lib.elf_parser.get_source_loc(self.bin_file, addr)
        while num_steps > 0:
            if forward:
                self.fedge(1)
            else:
                self.redge(1)
            nfile, nline = lib.elf_parser.get_source_loc(self.bin_file, addr)
            if nfile != file or nline != line:
                file, line = nfile, nline
                num_steps -= 1
            if is_module:
                addr = req_module[0].pc.value.as_int
            else:
                self.bkpt_namespace = self.model.signal_dict
                addr = eval(location, {}, self.bkpt_namespace)
        return ""

    def _model_has_dont_cares(self):
        for signal in self.model.signals:
            if 'x' in signal.value.as_str:
                return True
        return False

    def traceback(self):
        """Run simulation backwards until the last point where no signals were
        don't cares"""
        curr_time = self.model.sim_time
        if not self._model_has_dont_cares():
            raise InputException("Can't traceback if there isn't an 'x'!")
        while curr_time > 0:
            self.redge(1)
            curr_time = self.model.sim_time
            if not self._model_has_dont_cares():
                self.fedge(1)
                curr_time = self.model.sim_time
                break
        return f"First 'x' found at {curr_time}"

    @staticmethod
    def help_text():
        """Get the help text -- handle the 'help' command """
        htext = "HELP\n"
        max_command_width = max([len(command[0]) for command in COMMANDS]) + 4
        for command in COMMANDS:
            htext += f"{command[0]:^{max_command_width}}: {command[1]}\n"
        return htext

    def accept(self, _):
        """ Handle user input """
        out_text = ""
        text = self.runtime.input
        if not text:
            # Empty text (user pressed enter on empty prompt)
            if self.last_text:
                text = self.last_text
            else:
                return
        try:
            match = None
            for command in COMMANDS:
                match = re.match(command[2], text, re.MULTILINE)
                if match is not None:
                    user_command = command[0].split()[0]
                    break
            if match is None:
                raise InputException("Invalid Command!")

            groups = match.groups()
            if user_command == 'modules':
                out_text = self.list_modules()
            elif user_command == 'help':
                out_text = self.help_text()
            elif user_command == 'info':
                out_text = self.module_info(groups[1])
            elif user_command == 'fedge':
                out_text = self.fedge(groups[1])
            elif user_command == 'redge':
                out_text = self.redge(groups[1])
            elif user_command == 'break':
                out_text = self.breakpoint(groups[1])
            elif user_command == 'lsbrk':
                out_text = self.lsbrk()
            elif user_command == 'delete':
                out_text = self.delete(groups[1])
            elif user_command == 'run':
                out_text = self.run(groups[1])
            elif user_command == 'jump':
                out_text = self.jump(groups[1])
            elif user_command == 'where':
                out_text = self.where(groups[1], groups[2])
            elif user_command == 'step':
                out_text = self.step(True, groups[1], groups[2])
            elif user_command == 'rstep':
                out_text = self.step(False, groups[1], groups[2])
            elif user_command == 'clear':
                out_text = ""
            elif user_command == 'quit':
                self.runtime.application.exit()
            elif user_command == 'traceback':
                out_text = self.traceback()
            elif user_command == 'debugger':
                pdb.set_trace()
            else:
                raise InputException("Invalid Command!")
        except InputException as exception:
            out_text = f"ERROR: {str(exception)}"

        self.last_text = text
        self.runtime.update(out_text)


class Runtime():
    """ The front-end of the debugger -- initializes and launches the app"""
    def __init__(self, display, model, bin_file):
        assert model is not None and display is not None
        self.display = display
        if bin_file is not None and not os.path.isfile(bin_file):
            bin_file = None
        self.model = model
        body, input_field, time_field, output = self._create_windows()
        self.body = body
        self.input_field = input_field
        self.time_field = time_field
        self.output = output
        handler = InputHandler(self, self.model, bin_file)
        input_field.accept_handler = handler.accept
        self.update("")
        self.application = self._init_application()

    @property
    def input(self):
        """Get the current line of user input"""
        return self.input_field.text.lstrip().rstrip()

    def _create_windows(self):
        """Create all the windows of the display (input, output, debugger,
        text completer)"""
        module_names = [m.name for m in self.model.modules]
        search_field = SearchToolbar()
        # Generate the input text area
        input_field = TextArea(prompt='> ', style='class:arrow',
                               completer=ModuleCompleter(module_names),
                               search_field=search_field,
                               height=1,
                               multiline=False, wrap_lines=True)

        # Field to show current time
        end_time = str(self.model.get_end_time())
        time_field = TextArea(text="",
                              style='class:rprompt',
                              height=1,
                              width=len(end_time)*2 + 7,
                              multiline=False)

        output = Label(text="")
        self.display.update()

        # Create container with display window and input text area
        container = pt_containers.HSplit([
            self.display.get_top_view(),
            pt_containers.Window(height=1, char='-'),
            output,
            pt_containers.VSplit([input_field, time_field]),
            search_field
        ])

        # Floating menu for text completion
        completion_menu = CompletionsMenu(max_height=5, scroll_offset=1)
        body = pt_containers.FloatContainer(
            content=container,
            floats=[
                pt_containers.Float(
                    xcursor=True, ycursor=True, content=completion_menu
                )
            ]
        )

        return body, input_field, time_field, output

    def _init_application(self):
        style = Style([
            ('arrow', '#00aa00'),
            ('rprompt', 'bg:#c000c0 #ffffff')
        ])

        bindings = KeyBindings()

        @bindings.add('c-c')
        @bindings.add('c-q')
        @bindings.add('c-d')
        def _(event):
            " Pressing Ctrl-Q or Ctrl-C will exit the user interface. "
            event.app.exit()

        return Application(
            layout=Layout(self.body, focused_element=self.input_field),
            key_bindings=bindings,
            style=style,
            mouse_support=True,
            full_screen=True)

    def update_time(self):
        """Update the user's view of simulation time -- minimal progress
        redraw"""
        sim_time = self.model.sim_time
        if sim_time % (self.model.edge_time * 100) != 0:
            return
        curr_time = str(sim_time)
        time_str = curr_time + "/" + str(self.model.get_end_time())
        self.time_field.text = "Time: " + time_str
        # This is bad, but there isn't a another nice way to do it without
        # doing a whole lot of reworking with async
        self.application._redraw()

    def update(self, out_text):
        """Update the runtime and display"""
        curr_time = str(self.model.sim_time)
        time_str = curr_time + "/" + str(self.model.get_end_time())
        self.time_field.text = "Time: " + time_str
        self.output.text = out_text
        self.display.update()

    def start(self):
        """Start the debugger: initialize the display and run"""
        self.application.run()
