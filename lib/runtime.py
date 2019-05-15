#! /usr/bin/env python3

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.validation import Validator, ValidationError

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

class Runtime():
    def __init__(self, display, model):
        if display is not None:
            raise NotImplementedError("Displays aren't supported yet!")
        self.model = model
        self.prompt = None

    def create_prompt(self, module_names):
        prompt_style = Style.from_dict({
            'arrow': '#00aa00'
        })
        prompt_message = [
            ('class:arrow', '> '),
        ]
        completer = ModuleCompleter(module_names)
        self.prompt = (prompt_message, prompt_style, completer)

    def start(self):
        module_names = [m.get_name() for m in self.model.get_traced_modules()]
        self.create_prompt(module_names)
        session = PromptSession()
        sim_time = 0
        while 1:
            try:
                text = session.prompt(self.prompt[0], style=self.prompt[1],
                                      completer=self.prompt[2],
                                      validate_while_typing=False,
                                      validator=InputValidator())
            except EOFError:
                exit(0)
            except KeyboardInterrupt:
                exit(0)
            text = text.strip().split()
            if text[0] == 'list':
                for module in self.model.get_traced_modules():
                    print(module.get_name())
            elif text[0] == 'info':
                modules = self.model.get_traced_modules()
                req_module = [m for m in modules if m.get_name() == text[1]]
                if not req_module:
                    print("ERROR: Module not found!")
                else:
                    print(str(req_module[0]))
            elif text[0] == 'step':
                if len(text) == 2:
                    num_steps = int(text[1])
                else:
                    num_steps = 1
                sim_time = self.model.update(sim_time, num_steps)
            elif text[0] == 'time':
                print(sim_time)
