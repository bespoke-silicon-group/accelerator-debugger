#! /usr/bin/env python3

import abc
from collections import namedtuple

class Signal(namedtuple("Signal", ['symbol', 'name', 'value'])):
    """Signals are compsed of the VCD symbol that represents the signal,
    the name of the signal in the HW module that's it's part of, and
    its current value"""
    __slots__ = ()

    def __str__(self):
        return f"{self.name} ({self.symbol}): {self.value}"

# Stepping a simulation should just be stepping a HWModel, which
# steps all the module contained within it. Then, we can update
# each pane with the new information.
class HWModule(metaclass=abc.ABCMeta):
    """ Signals are tuples of (global_symbol, name_in_module, value) """
    def __init__(self, module_name, signals, vcd_data):
        self.data = vcd_data
        self.signals = []
        for signal in signals:
            symbol = self.data.get_symbol(signal)
            value = self.data.get_value(symbol, 0)
            self.signals.append(Signal(symbol, signal, value))
        self.name = module_name

    def get_signals(self):
        return self.signals

    def get_name(self):
        return self.name

    def __str__(self):
        desc = self.get_name() + ": "
        for signal in self.get_signals():
            desc += f"\n\t{str(signal)}"
        return desc

    def update_signals(self, time):
        for signal in self.get_signals():
            symbol = getattr(signal, 'symbol')
            setattr(signal, 'value', self.data.get_value(symbol, time))


class HWModel(metaclass=abc.ABCMeta):
    def get_traced_signals(self):
        signals = []
        for module in self.get_traced_modules():
            signals.extend(module.get_signals())
        return signals

    @abc.abstractmethod
    def get_traced_modules(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_step_time(self):
        raise NotImplementedError

    def update(self, time):
        for module in self.get_traced_modules():
            module.update_signals(time)


# class Regfile(HWModule):
#     def __init__(self, name, regs_signals):
#         self.signals = regs_signals
#         self.values = ['x'] * len(self.signals)
#         self.name = name

#     def getSignals(self):
#         return self.signals

#     def getName(self):
#         return self.name


# class Memory(HWModule):
#     def __init__(self, name, rdata, wdata, we):
#         self.signals = [rdata, wdata, we]
#         self.values = ['x'] * len(self.signals)
#         self.name = name

#     def getSignals(self):
#         return self.signals

#     def getName(self):
#         return self.name
