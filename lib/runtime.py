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

    ("step <n>", "Step <n> source code lines forward (default=1)",
     r"^(s|step)\s*(\d*)$"),

    ("rstep <n>", "Step <n> source code lines backward (default=1)",
     r"^(rs|rstep)\s*(\d*)$"),

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

    ("where <core>", "Give the source location for a given Core DebugModule",
     r"^(w|where)\s+(.+)$"),

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
    def __init__(self, input_field, output, time_field, model, display,
                 bin_file):
        self.input = input_field
        self.output = output
        self.time_field = time_field
        self.model = model
        self.display = display
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
                self.display.update()
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
                    self.display.update()
                    return f"Hit simulation end at time {self.model.sim_time}"
                num_edges -= 1
            self.display.update()
            return ""
        self.model.update(num_edges)
        self.display.update()
        if self.model.sim_time >= self.model.get_end_time():
            return f"Hit end of simulation at time {self.model.sim_time}"
        return ""

    def redge(self, num_edges):
        """ Handle the 'redge' and 'r' commands -- reverse clock edge"""
        if not num_edges:
            num_edges = '1'
        num_edges = int(num_edges)
        self.model.rupdate(num_edges)
        self.display.update()
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
        self.display.update()
        return ""

    def list_modules(self):
        """ Handle the modules command -- list all modules """
        out_text = ""
        for module in self.model.modules:
            out_text += f"* {module.name}\n"
        return out_text

    def parse_source(self, text):
        """ Handle the source command: display source around a given address"""
        if self.bin_file is None:
            raise InputException("Need to run with --binary to use source!")
        if len(text) == 1:
            raise InputException(f"Need to provide an address")
        address = int(text[1], 0)
        return lib.elf_parser.get_source_lines(self.bin_file, address)

    def where(self, location):
        """ Handle the `where` commmand: display source code that given core
        module is executing"""
        modules = self.model.modules
        address = None
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
        return lib.elf_parser.get_source_lines(self.bin_file, address)

    @staticmethod
    def help_text():
        """Get the help text -- handle the 'help' command """
        htext = "HELP\n"
        for command in COMMANDS:
            htext += f"{command[0]}: {command[1]}\n"
        return htext

    def get_time_str(self):
        """ Get current simulation time as a string """
        return str(self.model.sim_time)

    def accept(self, _):
        """ Handle user input """
        out_text = ""
        text = self.input.text.lstrip().rstrip()
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
                out_text = self.where(groups[1])
            elif user_command == 'step':
                out_text = "Unimplemented 'step'"
            elif user_command == 'rstep':
                out_text = "Unimplemented 'rstep'"
            elif user_command == 'clear':
                out_text = ""
            elif user_command == 'quit':
                exit(0)
            elif user_command == 'debugger':
                pdb.set_trace()
            else:
                raise InputException("Invalid Command!")
        except InputException as exception:
            out_text = f"ERROR: {str(exception)}"
        self.last_text = text
        time_str = self.get_time_str() + "/" + str(self.model.get_end_time())
        self.time_field.text = "Time: " + time_str

        self.output.text = out_text


class Runtime():
    """ The front-end of the debugger -- initializes and launches the app"""
    def __init__(self, display, model, bin_file):
        assert model is not None and display is not None
        self.model = model
        self.display = display
        if bin_file is not None and not os.path.isfile(bin_file):
            self.bin_file = None
        else:
            self.bin_file = bin_file

    def create_windows(self):
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
        time_str = str(self.model.sim_time) + "/" + end_time
        time_field = TextArea(text="Time: " + time_str,
                              style='class:rprompt',
                              height=1,
                              width=len(end_time)*2 + 7,
                              multiline=False)

        command_output = Label(text="")
        self.display.update()
        handler = InputHandler(input_field, command_output, time_field,
                               self.model, self.display, self.bin_file)

        # Create container with display window and input text area
        container = pt_containers.HSplit([
            self.display.get_top_view(),
            pt_containers.Window(height=1, char='-'),
            command_output,
            pt_containers.VSplit([input_field, time_field]),
            search_field
        ])

        # Floating menu for text completion
        completion_menu = CompletionsMenu(max_height=5, scroll_offset=1)
        body = pt_containers.FloatContainer(
            content=container,
            floats=[
                pt_containers.Float(xcursor=True,
                                    ycursor=True,
                                    content=completion_menu)])

        input_field.accept_handler = handler.accept
        return (body, input_field)

    def start(self):
        """Start the debugger: initialize the display and run"""
        body, input_field = self.create_windows()

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

        application = Application(
            layout=Layout(body, focused_element=input_field),
            key_bindings=bindings,
            style=style,
            mouse_support=True,
            full_screen=True)
        application.run()
