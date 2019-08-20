#! /usr/bin/env python3
"""Module to be used for testing with ex.vcd"""

from lib.hw_models import DebugModel, BasicModule, Memory
from lib.view import HSplit, View, Display


class TestModel(DebugModel):
    """ Debug model for data/ex.vpd; simple memory and signal values """
    def __init__(self, model_args):
        super(TestModel, self).__init__(100)
        signals = ['logic.data', 'logic.data_valid']
        self.add_module(BasicModule("r0_data", signals))
        self.add_module(Memory('memory', 'logic.waddr', 'logic.wdata',
                               'logic.tx_en', True))


class TestView(Display):
    """ The Display for viewing TestModel """
    def gen_top_view(self, model):
        return HSplit(View(model.get_module('memory')),
                      View(model.get_module('r0_data')))
