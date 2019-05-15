#! /usr/bin/env python3

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.document import Document
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings

COMMANDS = ['step', 'info', 'list', 'time']

class InputValidator(Validator):
    def validate(self, document):
        text = document.text.strip().split()
        if not text:
            return

        if text[0] not in COMMANDS:
            raise ValidationError(message="Invalid Command!")

        # step <digit>
        if text[0] == 'step':
            if len(text) == 2 and not text[1].isdigit():
                raise ValidationError(message="Step takes a number of steps!")
        # info <modulename>
        elif text[0] == "info":
            if len(text) != 2:
                raise ValidationError(message="info takes a module name!")


class ModuleCompleter(Completer):
    def __init__(self, module_names):
        self.module_names = module_names
        self.meta_dict = {}

    def get_completions(self, document, complete_event):
        words = []
        typed_words = str(document).strip().split()
        num_words = len(typed_words)
        words = []
        if num_words > 2 and document.find_backwards('info'):
            words = self.module_names
        elif num_words == 2:
            words = COMMANDS

        word_before_cursor = document.get_word_before_cursor(WORD=False)

        def word_matches(word):
            return word.startswith(word_before_cursor)

        for a in words:
            if word_matches(a):
                display_meta = self.meta_dict.get(a, '')
                yield Completion(a, -len(word_before_cursor),
                                 display_meta=display_meta)

class InputHandler():
    def __init__(self, input_field, output_field):
        self.input_field = input_field
        self.output_field = output_field
        self.sim_time = 0

    def accept(self, buff):
        out_text = ""
        text = self.input_field.text.strip().split()
        if text[0] == 'list':
            for module in self.model.get_traced_modules():
                out_text += f"{module.get_name()}\n"
        elif text[0] == 'info':
            modules = self.model.get_traced_modules()
            req_module = [m for m in modules if m.get_name() == text[1]]
            if not req_module:
                out_text += "ERROR: Module not found!\n"
            else:
                out_text += f"{str(req_module[0])}\n"
        elif text[0] == 'step':
            if len(text) == 2:
                num_steps = int(text[1])
            else:
                num_steps = 1
            self.sim_time = self.model.update(self.sim_time, num_steps)
        elif text[0] == 'time':
            out_text += str(self.sim_time)

        self.output_field.buffer.document = Document(text=out_text,
                                                     cursor_position=len(out_text))

class Runtime():
    def __init__(self, display, model):
        if display is not None:
            raise NotImplementedError("Displays aren't supported yet!")
        self.model = model
        self.prompt = None

    def create_prompt(self, module_names):
        prompt_message = [
            ('class:arrow', '> '),
        ]
                                      # validate_while_typing=False,
                                      # validator=InputValidator())
        return TextArea(prompt='> ', style='class:arrow',
                        completer=ModuleCompleter(module_names))

    def start(self):
        module_names = [m.get_name() for m in self.model.get_traced_modules()]
        input_field = self.create_prompt(module_names)
        output_field = TextArea(text="asdf")
        container = HSplit([
            output_field,
            Window(height=1, char='-'),
            input_field
        ])
        style = Style([
            ('arrow', '#00aa00')
        ])

        kb = KeyBindings()

        @kb.add('c-c')
        @kb.add('c-q')
        def _(event):
            " Pressing Ctrl-Q or Ctrl-C will exit the user interface. "
            event.app.exit()

        handler = InputHandler(input_field, output_field)

        input_field.accept_handler = handler.accept
        application = Application(
            layout=Layout(container, focused_element=input_field),
            mouse_support=True,
            key_bindings=kb,
            style=style,
            full_screen=True)
        application.run()
