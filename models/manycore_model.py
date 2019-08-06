#! /usr/bin/env python3

"""Model and View for a 2x2 celerity manycore"""

from lib.hw_models import DebugModel, BasicModule, Memory, Core
from lib.view import HSplit, VSplit, View, Display


class ManycoreModel(DebugModel):
    """DebugModel that describes a 2x2 celerity manycore"""
    def gen_rf_module(self, core_x, core_y):
        """ Generate module for the given x,y core for the register file"""
        # The RF module is a Memory DebugModule
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."

        addr = header + "rf_wa"
        wdata = header + "rf_wd"
        wen = header + "rf_wen"
        # Memory modules take an address signal, wdata signal, wen signal,
        # and the assertion level of the write enable signal (True for active
        # high). Memory modules have a few additional flags:
        #
        # segments=['a', ('b', 'f'), '10']
        #   Give a list of memory locations that we want to track or tuples
        #   that describe a range of memory locations that we want to track.
        #   The above example would track address 0xa, 0xb-0xf, and 0x10.
        #
        # size=32
        #   If `size` is given, fill in memory locations that haven't been
        #   written with don't cares in the display. If a size isn't given, we
        #   lazily track memory locations as they are written to.
        #
        # show_signals=True
        #   If true, show the address, wdata, and wen signals in the display
        #   panel for this module. If false, only memory locations are shown.
        #
        self.add_module(Memory(f"rf_{core_y}_{core_x}", addr, wdata, wen,
                               True, size=32,
                               show_signals=True))

    def gen_inst_module(self, core_x, core_y):
        """DebugModule for signals that describe the current instruction"""
        # The Inst module is a Core Module -- useful for tracking program
        # counters (and correlating with lines of source code).
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."
        inst_sigs = []
        pc_sig = header + "pc_real"
        inst_sigs.append(header + "exe.pc_plus4")
        inst_sigs.append(header + "id.pc_plus4")
        # The second argument to a Core module (after the name) is the name of
        # the program counter signal. The program counter needs to correlate
        # with addresses in the binary (if one is provided) -- in this case,
        # we needed to make a new signal, pc_real, that adds the extra two bits
        # of zeros that would typically be ommitted.
        # The third argument is a list of signals that should also be tracked
        # by this module.
        self.add_module(Core(f"inst_{core_y}_{core_x}", pc_sig, inst_sigs))

    def gen_wmem_module(self, core_x, core_y):
        """DebugModule for signals that write to the local memory"""
        # The wmem module is a BasicModule
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z.hobbit0."
        addr = header + 'to_mem_o.addr'
        wdata = header + 'to_mem_o.payload.write_data'
        isload = header + 'mem.decode.is_load_op'
        isstr = header + 'mem.decode.is_store_op'
        stall = header + 'stall'
        mem_sigs = [addr, wdata, isload, isstr, stall]
        # Basic Modules only take a list of signals to be tracked
        self.add_module(BasicModule(f"wmem_{core_y}_{core_x}", mem_sigs))

    def gen_remote_module(self, core_x, core_y):
        """DebugModule for signals used in accessing remote cores"""
        header = f"test_bsg_manycore.UUT.y[{core_y+1}].x[{core_x}].tile."
        header += "proc.h.z."
        lout = header + 'launching_out'
        addr = header + 'data_o_debug.addr'
        data = header + 'data_o_debug.payload.data'
        x_cord = header + 'data_o_debug.y_cord'
        y_cord = header + 'data_o_debug.x_cord'
        remote_sigs = [lout, addr, data, x_cord, y_cord]
        self.add_module(BasicModule(f"remote_{core_y}_{core_x}", remote_sigs))

    def __init__(self):
        # DebugModel's __init__ method takes a clock period, in our case,
        # the clock toggles edges every 10ps, so a full clock period would be
        # 20ps.
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

        # This represents a fairly standard paradigm for creating Displays.
        # We start by creating a "View" of each module that we want to display.
        for i in range(2):
            for j in range(2):
                regs.append(View(model.get_module(f"rf_{i}_{j}")))
                insts.append(View(model.get_module(f"inst_{i}_{j}")))
                wmem.append(View(model.get_module(f"wmem_{i}_{j}")))
                remote.append(View(model.get_module(f"remote_{i}_{j}")))

        # Then, we arrange the views with HSplits and VSplits.
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
