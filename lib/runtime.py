#! /usr/bin/env python3
""" The front end of the application:
    * Parsing user input is done by the InputHandler
    * Text completion is done by the ModuleCompleter
    * Runtime initializes and runs the application
"""


from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.widgets import TextArea, SearchToolbar, Label
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.menus import CompletionsMenu
import prompt_toolkit.layout.containers as pt_containers

COMMANDS = ['step', 'info', 'list', 'time', 'help', 'breakpoint', 'lsbrk',
            'delete', 'run', 'clear']


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
        elif num_words == 1 and typed[0] in COMMANDS:
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
    def __init__(self, input_field, command_output, model, display):
        self.input_field = input_field
        self.command_output = command_output
        self.model = model
        self.display = display
        self.bkpt_namespace = {}
        for module in self.model.get_traced_modules():
            self.bkpt_namespace[module.get_name()] = module.get_signal_dict()
        self.breakpoints = []
        self.next_bkpt_num = 0

    def parse_step(self, text):
        """ Handle the 'step' command """
        if len(text) == 2:
            num_steps = int(text[1])
        else:
            num_steps = 1
        for step in range(num_steps):
            self.model.step()
            sim_time = self.model.sim_time
            for module in self.model.get_traced_modules():
                self.bkpt_namespace[module.get_name()] = module.get_signal_dict()
            for num, cond in self.breakpoints:
                if eval(cond, {}, self.bkpt_namespace):
                    self.display.update()
                    return f"Hit breakpoint {num} at time {sim_time}"
            if sim_time >= self.model.get_end_time():
                self.display.update()
                return f"Hit end of simulation at time {self.model.sim_time}"

        self.display.update()
        return ""

    def parse_info(self, text):
        """ Handle the 'info' command """
        modules = self.model.get_traced_modules()
        if len(text) == 1:
            raise InputException("info takes a module name")
        req_module = [m for m in modules if m.get_name() == text[1]]
        if not req_module:
            raise InputException("Module not found!")
        return f"{str(req_module[0])}\n"

    def parse_breakpoint(self, text):
        if len(text) <= 1:
            raise InputException("Breakpoint takes a condition")
        condition = " ".join(text[1:])
        # Convert commonly used C expressions to python, != is hard though
        condition = condition.replace('&&', 'and')
        condition = condition.replace('||', 'or')
        condition = condition.replace('!', 'not')
        modules = self.model.get_traced_modules()
        try:
            current_cond = eval(condition, {}, self.bkpt_namespace)
        except:
            raise InputException("Invalid breakpoint condition!")
        if type(current_cond) != bool:
            raise InputException("Breakpoint condition not boolean!")

        bkpt_num = self.next_bkpt_num
        self.next_bkpt_num += 1
        self.breakpoints.append((bkpt_num, condition))
        return f"Breakpoint {bkpt_num}: {condition}"

    def lsbrk(self, text):
        out_text = ""
        for bkpt_num, condition in self.breakpoints:
            out_text += f"Breakpoint {bkpt_num}: {condition}\n"
        return out_text[:-1]  # Strip final newline

    def delete(self, text):
        if len(text) <= 1:
            raise InputException("Need to provide a breakpoint number!")
        bkpt_num = int(text[1])
        for i, bkpt in enumerate(self.breakpoints):
            if bkpt[0] == bkpt_num:
                self.breakpoints.pop(i)
                return f"Removed breakpoint {bkpt_num}"
        raise InputException(f"Breakpoint {bkpt_num} not found!")

    def run(self, text):
        curr_time = self.model.sim_time
        if len(text) == 1:  # Run until breakpoint or finish
            end_time = self.model.end_time
        else:
            end_time = int(text[1])
            if end_time < curr_time:
                raise InputException("Time must be later than current time")
        steps = (end_time - curr_time) // self.model.step_time
        return self.parse_step(f"step {steps}".split())

    @staticmethod
    def help_text():
        htext = "HELP:\n    step <n>: Step the simulation n times\n"
        htext += "    info <module_name>: Print the status of a given module\n"
        htext += "    time: Print the current simulation time\n"
        htext += "    breakpoint <cond>: Set a breakpoint for a given condition\n"
        htext += "    lsbrk: List set breakpoints\n"
        htext += "    delete <num>: Delete a breakpoint, specified by number\n"
        htext += "    run <time>: Run simulation until a specified time\n"
        htext += "    clear: Clear the output window\n"
        htext += "    help: Print this text"
        return htext

    def get_time_str(self):
        return str(self.model.sim_time)

    def accept(self, _):
        """ Handle user input """
        out_text = ""
        text = self.input_field.text.strip().split()
        if not text:
            return
        try:
            if text[0] == 'list':
                for module in self.model.get_traced_modules():
                    out_text += f"* {module.get_name()}\n"
            elif text[0] == 'help':
                out_text = self.help_text()
            elif text[0] == 'info':
                out_text = self.parse_info(text)
            elif text[0] == 'step' or text[0] == 's':
                out_text = self.parse_step(text)
            elif text[0] == 'time':
                out_text = self.get_time_str()
            elif text[0] == 'breakpoint' or text[0] == 'b':
                out_text = self.parse_breakpoint(text)
            elif text[0] == 'lsbrk':
                out_text = self.lsbrk(text)
            elif text[0] == 'delete':
                out_text = self.delete(text)
            elif text[0] == 'run':
                out_text = self.run(text)
            elif text[0] == 'clear':
                out_text = ""
            else:
                raise InputException("Invalid Command!")
        except InputException as exception:
            out_text = f"ERROR: {str(exception)}"

        self.command_output.text = out_text


class Runtime():
    """ The front-end of the debugger -- initializes and launches the app"""
    def __init__(self, display, model):
        assert model is not None and display is not None
        self.model = model
        self.display = display

    def start(self):
        """Start the debugger: initialize the display and run"""
        module_names = [m.get_name() for m in self.model.get_traced_modules()]
        search_field = SearchToolbar()
        input_field = TextArea(prompt='> ', style='class:arrow',
                               completer=ModuleCompleter(module_names),
                               search_field=search_field,
                               height=1,
                               multiline=False, wrap_lines=True)

        # output_field = TextArea(text="")
        command_output = Label(text="")
        self.display.update()
        handler = InputHandler(input_field, command_output,
                               self.model, self.display)

        container = pt_containers.HSplit([
            self.display.get_top_view(),
            # output_field,
            pt_containers.Window(height=1, char='-'),
            command_output,
            input_field,
            search_field
        ])

        completion_menu = CompletionsMenu(max_height=5, scroll_offset=1)
        body = pt_containers.FloatContainer(
            content=container,
            floats=[
                pt_containers.Float(xcursor=True,
                                    ycursor=True,
                                    content=completion_menu)])


        input_field.accept_handler = handler.accept

        style = Style([
            ('arrow', '#00aa00')
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
