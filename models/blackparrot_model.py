#! /usr/bin/env python3

"""Model and View for a single BP core"""

from lib.hw_models import DebugModel, BasicModule, Memory, Core
from lib.view import HSplit, VSplit, View, Display

class BlackParrotModel(DebugModel):
    """DebugModel that describes a single BlackParrot core"""
    def gen_rf_module(self, core_id):
      """ Generate module for the given core id for the register file"""
      # The RF module is a Memory DebugModule
      header = f"test_bp.tb.wrapper.dut.cc.bp_top.rof1[{core_id}].tile."
      header += "core.be.be_calculator."

      addr = header + "int_regfile.rd_addr_i"
      wdata = header + "int_regfile.rd_data_i"
      wen = header + "int_regfile.rd_w_v_i"

      self.add_module(Memory(f"rf_{core_id}", addr, wdata, wen,
                             True, size=32,
                             show_signals=True))

    def gen_inst_module(self, core_id):
      """ Generate model for the given core id for the instructions"""
      header = f"test_bp.tb.wrapper.dut.cc.bp_top.rof1[{core_id}].tile."
      header += "core.be."

      pc_sig = header + "be_checker.expected_npc"
      inst_sigs = []
      inst_sigs.append(header + "be_calculator.pc_mem3_o")
      inst_sigs.append(header + "be_calculator.instr_mem3_o")
      #inst_sigs.append(header + "be_calculator.calc_stage_r[0].pc")
      #inst_sigs.append(header + "be_calculator.calc_stage_r[1].pc")
      #inst_sigs.append(header + "be_calculator.calc_stage_r[2].pc")
      #inst_sigs.append(header + "be_calculator.calc_stage_r[3].pc")
      #inst_sigs.append(header + "be_calculator.calc_stage_r[4].pc")

      self.add_module(Core(f"inst_{core_id}", pc_sig, inst_sigs))


    def __init__(self, model_args):
        super(BlackParrotModel, self).__init__(20)
        self.gen_rf_module(0)
        self.gen_inst_module(0)


class BlackParrotView(Display):
    """View for debugging BlackParrot"""
    def gen_top_view(self, model):
      regs = []
      insts = []

      i = 0
      regs.append(View(model.get_module(f"rf_{i}")))
      insts.append(View(model.get_module(f"inst_{i}")))
      regs = HSplit(regs[0], insts[0])

      return regs

