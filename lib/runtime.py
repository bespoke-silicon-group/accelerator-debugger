#! /usr/bin/env python3
""" The front end of the application:
    * Parsing user input is done by the InputHandler
    * Text completion is done by the ModuleCompleter
    * Runtime initializes and runs the application
"""


import pdb

import os.path
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.widgets import TextArea, SearchToolbar, Label
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.menus import CompletionsMenu
import prompt_toolkit.layout.containers as pt_containers
import lib.elf_parser

COMMANDS = ['step', 'info', 'list', 'help', 'breakpoint', 'lsbrk',
            'delete', 'run', 'clear', 'rstep', 'go', 'source']


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
        words = COMMANDS
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

    def parse_step(self, text):
        """ Handle the 'step' command """
        if len(text) == 2:
            num_steps = int(text[1])
        else:
            num_steps = 1
        if self.breakpoints:
            while num_steps > 0:
                self.model.step()
                sim_time = self.model.sim_time
                for module in self.model.modules:
                    signals = module.signal_dict
                    self.bkpt_namespace[module.name] = signals
                for num, _, cond in self.breakpoints:
                    if eval(cond, {}, self.bkpt_namespace):
                        self.display.update()
                        return f"Hit breakpoint {num} at time {sim_time}"
                if sim_time >= self.model.get_end_time():
                    self.display.update()
                    return f"Hit simulation end at time {self.model.sim_time}"
                num_steps -= 1
            self.display.update()
            return ""
        self.model.update(num_steps)
        self.display.update()
        if self.model.sim_time >= self.model.get_end_time():
            return f"Hit end of simulation at time {self.model.sim_time}"
        return ""

    def parse_rstep(self, text):
        """ Handle the 'rstep' and 'rs' commands -- reverse step"""
        if len(text) == 2:
            num_steps = int(text[1])
        else:
            num_steps = 1
        self.model.rupdate(num_steps)
        self.display.update()
        return ""

    def parse_info(self, text):
        """ Handle the 'info' command """
        modules = self.model.modules
        if len(text) == 1:
            raise InputException("info takes a module name")
        req_module = [m for m in modules if m.name == text[1]]
        if not req_module:
            raise InputException("Module not found!")
        return f"{str(req_module[0])}\n"

    def parse_breakpoint(self, text):
        """ Handle the 'breakpoint' command """
        if len(text) <= 1:
            raise InputException("Breakpoint takes a condition")
        condition = " ".join(text[1:])
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

    def lsbrk(self, _):
        """ Handle the lsbrk command -- list breakpoints """
        out_text = ""
        for bkpt_num, condition, _ in self.breakpoints:
            out_text += f"Breakpoint {bkpt_num}: {condition}\n"
        return out_text[:-1]  # Strip final newline

    def delete(self, text):
        """ Handle the delete command -- delete breakpoint """
        if len(text) <= 1:
            raise InputException("Need to provide a breakpoint number!")
        bkpt_num = int(text[1])
        for i, bkpt in enumerate(self.breakpoints):
            if bkpt[0] == bkpt_num:
                self.breakpoints.pop(i)
                return f"Removed breakpoint {bkpt_num}"
        raise InputException(f"Breakpoint {bkpt_num} not found!")

    def run(self, text):
        """ Handle the run command -- forward execution to a given time """
        curr_time = self.model.sim_time
        if len(text) == 1:  # Run until breakpoint or finish
            end_time = self.model.end_time
        else:
            end_time = int(text[1])
            if end_time < curr_time:
                raise InputException("Time must be later than current time")
        steps = (end_time - curr_time) // self.model.step_time
        return self.parse_step(f"step {steps}".split())

    def parse_go(self, text):
        """ Handle the go command -- jump to a given time"""
        if len(text) == 1:
            raise InputException(f"Need to provide a time with go!")
        dest_time = int(text[1])
        curr_time = self.model.sim_time
        steps = abs(dest_time - curr_time) // self.model.step_time
        if dest_time < curr_time:
            self.model.rupdate(steps)
        else:
            self.model.update(steps)
        self.display.update()
        return ""

    def parse_list(self, _):
        """ Handle the list command -- list all modules """
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


    @staticmethod
    def help_text():
        """Get the help text -- handle the 'help' command """
        htext = "HELP:\n    step <n>: Step the simulation n times\n"
        htext += "    rstep <n>: Step the simulation backwards n times\n"
        htext += "    info <module_name>: Print the status of a given module\n"
        htext += "    breakpoint <cond>: Set a breakpoint given a condition\n"
        htext += "       breakpoint conditions are written in Python syntax\n"
        htext += "    lsbrk: List set breakpoints\n"
        htext += "    delete <num>: Delete a breakpoint, specified by number\n"
        htext += "    run <time>: Run simulation until a specified time\n"
        htext += "    go <time>: Jump to a given time, ignoring breakpoints\n"
        htext += "    clear: Clear the output window\n"
        htext += "    help: Print this text"
        return htext

    def get_time_str(self):
        """ Get current simulation time as a string """
        return str(self.model.sim_time)

    def accept(self, _):
        """ Handle user input """
        out_text = ""
        text = self.input.text.strip().split()
        if not text:
            # Empty text (user pressed enter on empty prompt)
            if self.last_text:
                text = self.last_text
            else:
                return
        try:
            if text[0] == 'list':
                out_text = self.parse_list(text)
            elif text[0] == 'help':
                out_text = self.help_text()
            elif text[0] == 'info':
                out_text = self.parse_info(text)
            elif text[0] == 'step' or text[0] == 's':
                out_text = self.parse_step(text)
            elif text[0] == 'rstep' or text[0] == 'rs':
                out_text = self.parse_rstep(text)
            elif text[0] == 'breakpoint' or text[0] == 'b':
                out_text = self.parse_breakpoint(text)
            elif text[0] == 'lsbrk':
                out_text = self.lsbrk(text)
            elif text[0] == 'delete':
                out_text = self.delete(text)
            elif text[0] == 'run':
                out_text = self.run(text)
            elif text[0] == 'go':
                out_text = self.parse_go(text)
            elif text[0] == 'clear':
                out_text = ""
            elif text[0] == 'source':
                out_text = self.parse_source(text)
            elif text[0] == 'debugger':
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
