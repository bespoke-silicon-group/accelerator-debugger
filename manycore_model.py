#! /usr/bin/env python3

import hw_models

class ManycoreModel(hw_models.HWModel):

    def get_traced_modules(self):
        print("asdf")

    def get_step_time(self):
        return 10
