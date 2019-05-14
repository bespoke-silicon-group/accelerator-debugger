#! /usr/bin/env python3

import hw_models

class ManycoreModel(hw_models.HWModel):
    def __init__(self, vcd_data):
        self.data = vcd_data
        self.modules = []
        import code; code.interact(local=locals())


    def get_traced_modules(self):
        print("asdf")

    def get_step_time(self):
        return 10
