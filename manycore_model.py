#! /usr/bin/env python3

from lib.hw_models import HWModel, BasicModule, Memory
from lib.view import *


class ManycoreModel(HWModel):
    def __init__(self):
        self.modules = []
        r0_data_signals = []
        for i in range(2):
            for j in range(2):
                header = f"test_bsg_manycore.UUT.y[{i+1}].x[{j}].tile."
                header += "proc.h.z.vanilla_core."
                r0_data_signals.append(header + "rf_0.r0_data_o[31:0]")
                addr = header + "rf_wa[4:0]"
                wdata = header + "rf_wd[31:0]"
                wen = header + "rf_wen"
                self.modules.append(Memory(f"rf_{i}_{j}", addr, wdata, wen,
                                           True, size=32,
                                           segments=['a', 'b', '17', '18'],
                                           show_signals=False))
                inst_sigs = []
                inst_sigs.append(header + "exe.pc_plus4[31:0]")
                self.modules.append(BasicModule(f"inst_{i}_{j}", inst_sigs))

                addr = header + 'to_mem_o.addr[31:0]'
                wdata = header + 'to_mem_o.payload.write_data[31:0]'
                isload = header + 'mem.decode.is_load_op'
                isstr = header + 'mem.decode.is_store_op'
                stall = header + 'stall'
                mem_sigs = [addr, wdata, isload, isstr, stall]
                self.modules.append(BasicModule(f"wmem_{i}_{j}", mem_sigs))

                header = f"test_bsg_manycore.UUT.y[{i+1}].x[{j}].tile."
                header += "proc.h.z."
                lout = header + 'launching_out'
                addr = header + 'data_o_debug.addr[28:0]'
                data = header + 'data_o_debug.payload.data[31:0]'
                x = header + 'data_o_debug.y_cord[1:0]'
                y = header + 'data_o_debug.x_cord[0:0]'
                remote_sigs = [lout, addr, data, x, y]
                self.modules.append(BasicModule(f"remote_{i}_{j}",
                                                remote_sigs))

        self.modules.append(BasicModule("r0_data", r0_data_signals))
        super(ManycoreModel, self).__init__()

    def get_traced_modules(self):
        return self.modules

    @property
    def step_time(self):
        return 20


class ManycoreView(Display):
    def gen_top_view(self, model):
        regs = []
        insts = []
        wmem = []
        remote = []
        for i in range(2):
            for j in range(2):
                regs.append(View(model.get_module(f"rf_{i}_{j}")))
                insts.append(View(model.get_module(f"inst_{i}_{j}")))
                wmem.append(View(model.get_module(f"wmem_{i}_{j}")))
                remote.append(View(model.get_module(f"remote_{i}_{j}")))

        regs = HSplit(
            VSplit(
                HSplit(VSplit(regs[0], remote[0]),
                       VSplit(insts[0], wmem[0])),
                HSplit(VSplit(regs[1], remote[1]),
                       VSplit(insts[1], wmem[1]))),
            VSplit(
                HSplit(VSplit(regs[2], remote[2]),
                       VSplit(insts[2], wmem[2])),
                HSplit(VSplit(regs[3], remote[3]),
                       VSplit(insts[3], wmem[3])))
        )
        return regs

