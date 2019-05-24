#! /usr/bin/env python3

from lib.hw_models import HWModel, BasicModule, Memory
from lib.view import *


class ManycoreModel(HWModel):
    def __init__(self):
        self.modules = []
        signals = []
        for i in range(2):
            for j in range(2):
                header = f"test_bsg_manycore.UUT.y[{i+1}].x[{j}].tile."
                header += "proc.h.z.vanilla_core."
                signals.append(header + "rf_0.r0_data_o[31:0]")
                addr = header + "rf_wa[4:0]"
                wdata = header + "rf_wd[31:0]"
                wen = header + "rf_wen"
                self.modules.append(Memory(f"rf_{i}_{j}", addr, wdata, wen,
                                           True, size=32,
                                           segments=['a', 'b', '17', '18']))
        self.modules.append(BasicModule("r0_data", signals))
        super(ManycoreModel, self).__init__()

    def get_traced_modules(self):
        return self.modules

    def get_step_time(self):
        return 10


class ManycoreView(Display):
    def gen_top_view(self, model):
        regs = []
        for i in range(2):
            for j in range(2):
                regs.append(model.get_module(f"rf_{i}_{j}"))

        regs = HSplit(VSplit(View(regs[0]), View(regs[1])),
                      VSplit(View(regs[2]), View(regs[3])))
        return regs

