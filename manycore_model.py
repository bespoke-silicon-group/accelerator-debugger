#! /usr/bin/env python3

"""Model and View for a 2x2 celerity manycore"""

from lib.hw_models import DebugModel, BasicModule, Memory, Core
from lib.view import HSplit, VSplit, View, Display


class ManycoreModel(DebugModel):
    """DebugModel that describes a 2x2 celerity manycore"""
    def gen_rf_module(self, core_x, core_y):
        """ Generate module for the given x,y core for the register file"""
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.vanilla_core."

        addr = header + "rf_wa[4:0]"
        wdata = header + "rf_wd[31:0]"
        wen = header + "rf_wen"
        self.add_module(Memory(f"rf_{core_y}_{core_x}", addr, wdata, wen,
                               True, size=32,
                               segments=['a', 'b', '17', '18'],
                               show_signals=False))

    def gen_inst_module(self, core_x, core_y):
        """DebugModule for signals that describe the current instruction"""
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.vanilla_core."
        inst_sigs = []
        pc_sig = header + "pc_n[21:0]"
        inst_sigs.append(header + "exe.pc_plus4[31:0]")
        inst_sigs.append(header + "id.pc_plus4[31:0]")
        self.add_module(Core(f"inst_{core_y}_{core_x}", pc_sig, inst_sigs))

    def gen_wmem_module(self, core_x, core_y):
        """DebugModule for signals that write to the local memory"""
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.vanilla_core."
        addr = header + 'to_mem_o.addr[31:0]'
        wdata = header + 'to_mem_o.payload.write_data[31:0]'
        isload = header + 'mem.decode.is_load_op'
        isstr = header + 'mem.decode.is_store_op'
        stall = header + 'stall'
        mem_sigs = [addr, wdata, isload, isstr, stall]
        self.add_module(BasicModule(f"wmem_{core_y}_{core_x}", mem_sigs))

    def gen_remote_module(self, core_x, core_y):
        """DebugModule for signals used in accessing remote cores"""
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z."
        lout = header + 'launching_out'
        addr = header + 'data_o_debug.addr[28:0]'
        data = header + 'data_o_debug.payload.data[31:0]'
        x_cord = header + 'data_o_debug.y_cord[1:0]'
        y_cord = header + 'data_o_debug.x_cord[0:0]'
        remote_sigs = [lout, addr, data, x_cord, y_cord]
        self.add_module(BasicModule(f"remote_{core_y}_{core_x}", remote_sigs))

    def __init__(self):
        super(ManycoreModel, self).__init__(20)
        for i in range(2):  # X dimension
            for j in range(2):  # Y Dimensiohn
                self.gen_remote_module(j, i)
                self.gen_wmem_module(j, i)
                self.gen_rf_module(j, i)
                self.gen_inst_module(j, i)


class ManycoreView(Display):
    """View for debugging the celerity manycore"""
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
