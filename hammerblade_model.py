#! /usr/bin/env python3

"""Model and View for a 4x4 Hammerblade Manycore"""

from lib.hw_models import DebugModel, BasicModule, Memory
from lib.view import HSplit, VSplit, View, Display


class HammerbladeModel(DebugModel):
    """DebugModel that describes a 2x2 Hammerblade Manycore"""
    def gen_rf_module(self, core_x, core_y):
        """ Generate module for the given x,y core for the register file"""
        header = f"tb.card.fpga.CL.manycore_wrapper.manycore.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."

        addr = header + "rf_wa[4:0]"
        wdata = header + "rf_wd[31:0]"
        wen = header + "rf_wen"
        self.add_module(Memory(f"rf_{core_y}_{core_x}", addr, wdata, wen,
                               True, size=32,
                               segments=['a', 'b', '17', '18'],
                               show_signals=False))

    def gen_inst_module(self, core_x, core_y):
        """DebugModule for signals that describe the current instruction"""
        header = f"tb.card.fpga.CL.manycore_wrapper.manycore.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."

        inst_sigs = [header + "exe.pc_plus4[31:0]"]
        self.add_module(BasicModule(f"inst_{core_y}_{core_x}", inst_sigs))

    def gen_wmem_module(self, core_x, core_y):
        """DebugModule for signals that write to the local memory"""
        header = f"tb.card.fpga.CL.manycore_wrapper.manycore.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."

        addr = header + 'to_mem_o.addr[31:0]'
        wdata = header + 'to_mem_o.payload.write_data[31:0]'
        isload = header + 'mem.decode.is_load_op'
        isstr = header + 'mem.decode.is_store_op'
        stall = header + 'stall'
        mem_sigs = [addr, wdata, isload, isstr, stall]
        self.add_module(BasicModule(f"wmem_{core_y}_{core_x}", mem_sigs))

    def gen_remote_module(self, core_x, core_y):
        """DebugModule for signals used in accessing remote cores"""
        header = f"tb.card.fpga.CL.manycore_wrapper.manycore.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z."

        lout = header + 'launching_out'
        addr = header + 'data_o_debug.addr[27:0]'
        data = header + 'data_o_debug.payload.data[31:0]'
        x_cord = header + 'data_o_debug.y_cord[2:0]'
        y_cord = header + 'data_o_debug.x_cord[1:0]'
        remote_sigs = [lout, addr, data, x_cord, y_cord]
        self.add_module(BasicModule(f"remote_{core_y}_{core_x}", remote_sigs))

    def __init__(self):
        super(HammerbladeModel, self).__init__(20)
        for i in range(4):  # X dimension
            for j in range(4):  # Y Dimensiohn
                self.gen_remote_module(j, i)
                self.gen_wmem_module(j, i)
                self.gen_rf_module(j, i)
                self.gen_inst_module(j, i)


class HammerbladeView(Display):
    """View for debugging the Hammerblade Manycore"""
    def gen_top_view(self, model):
        regs = []
        insts = []
        wmem = []
        remote = []
        for i in range(4):
            for j in range(4):
                regs.append(View(model.get_module(f"rf_{i}_{j}")))
                insts.append(View(model.get_module(f"inst_{i}_{j}")))
                wmem.append(View(model.get_module(f"wmem_{i}_{j}")))
                remote.append(View(model.get_module(f"remote_{i}_{j}")))

        regs = VSplit(
            VSplit(
                HSplit(
                    HSplit(
                        VSplit(VSplit(regs[0], remote[0]),
                               VSplit(insts[0], wmem[0])),
                        VSplit(VSplit(regs[1], remote[1]),
                               VSplit(insts[1], wmem[1]))),
                    HSplit(
                        HSplit(VSplit(regs[2], remote[2]),
                               VSplit(insts[2], wmem[2])),
                        HSplit(VSplit(regs[3], remote[3]),
                               VSplit(insts[3], wmem[3])))
                ),
                HSplit(
                    HSplit(
                        VSplit(VSplit(regs[4], remote[4]),
                               VSplit(insts[4], wmem[4])),
                        VSplit(VSplit(regs[5], remote[5]),
                               VSplit(insts[5], wmem[5]))),
                    HSplit(
                        HSplit(VSplit(regs[6], remote[6]),
                               VSplit(insts[6], wmem[6])),
                        HSplit(VSplit(regs[7], remote[7]),
                               VSplit(insts[7], wmem[7])))
                )),
            VSplit(
                HSplit(
                    HSplit(
                        VSplit(VSplit(regs[8], remote[8]),
                               VSplit(insts[8], wmem[8])),
                        VSplit(VSplit(regs[9], remote[9]),
                               VSplit(insts[9], wmem[9]))),
                    HSplit(
                        HSplit(VSplit(regs[10], remote[10]),
                               VSplit(insts[10], wmem[10])),
                        HSplit(VSplit(regs[11], remote[11]),
                               VSplit(insts[11], wmem[11])))
                ),
                HSplit(
                    HSplit(
                        VSplit(VSplit(regs[12], remote[12]),
                               VSplit(insts[12], wmem[12])),
                        VSplit(VSplit(regs[13], remote[13]),
                               VSplit(insts[13], wmem[13]))),
                    HSplit(
                        HSplit(VSplit(regs[14], remote[14]),
                               VSplit(insts[14], wmem[14])),
                        HSplit(VSplit(regs[15], remote[15]),
                               VSplit(insts[15], wmem[15])))
                )))
        return regs



