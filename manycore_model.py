#! /usr/bin/env python3

from lib.hw_models import HWModel, HWModule


class ManycoreModel(HWModel):
    def __init__(self):
        self.modules = []
        signals = []
        for i in range(2):
            for j in range(2):
                signals.append(f"test_bsg_manycore.UUT.y[{i+1}].x[{j}].tile.\
proc.h.z.vanilla_core.rf_0.rf_mem.synth.r0_data_o[31:0]")
        self.modules.append(HWModule("r0_data", signals))

    def get_traced_modules(self):
        return self.modules

    def get_step_time(self):
        return 10
