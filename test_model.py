#! /usr/bin/env python3
"""Module to be used for testing with ex.vcd"""

from lib.hw_models import HWModel, HWModule


class TestModel(HWModel):
    def __init__(self):
        self.modules = []
        signals = ['logic.data', 'logic.data_valid']
        self.modules.append(HWModule("r0_data", signals))

    def get_traced_modules(self):
        return self.modules

    def get_step_time(self):
        return 100
