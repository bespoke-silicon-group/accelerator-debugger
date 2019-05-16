#! /usr/bin/env python3
"""Module to be used for testing with ex.vcd"""

from lib.hw_models import HWModel, BasicModule, Memory
from lib.view import *


class TestModel(HWModel):
    def __init__(self):
        self.modules = []
        signals = ['logic.data', 'logic.data_valid']
        self.modules.append(BasicModule("r0_data", signals))
        self.modules.append(Memory('mem', 'logic.waddr', 'logic.wdata',
                                       'logic.tx_en', True))

    def get_traced_modules(self):
        return self.modules

    def get_step_time(self):
        return 100

class TestView(Display):
    def gen_top_view(self, model):
        return HSplit(View(model.get_module('mem')),
                      View(model.get_module('r0_data')))
