#! /usr/bin/env python3

import abc


class Signal():
    """Signals are compsed of the VCD symbol that represents the signal,
    the name of the signal in the HW module that's it's part of, and
    its current value"""
    def __init__(self, symbol, name, value):
        self.symbol = symbol
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name} ({self.symbol}): {self.value}"


# Stepping a simulation should just be stepping a HWModel, which
# steps all the module contained within it. Then, we can update
# each pane with the new information.
class HWModule(metaclass=abc.ABCMeta):
    """ Signals are tuples of (global_symbol, name_in_module, value) """
    def __init__(self, module_name, signals):
        self.signal_names = signals
        self.signals = []
        self.name = module_name

    def set_data(self, data):
        self.data = data
        for signal in self.signal_names:
            symbol = self.data.get_symbol(signal)
            value = self.data.get_value(symbol, 0)
            self.signals.append(Signal(symbol, signal, value))

    def get_signal_names(self):
        return self.signal_names

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
            signal.value = self.data.get_value(signal.symbol, time)


class HWModel(metaclass=abc.ABCMeta):
    def get_traced_signals(self):
        signals = []
        for module in self.get_traced_modules():
            signals.extend(module.get_signals())
        return signals

    def get_signal_names(self):
        names = []
        for module in self.get_traced_modules():
            names.extend(module.get_signal_names())
        return names

    @abc.abstractmethod
    def get_traced_modules(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_step_time(self):
        raise NotImplementedError

    def update(self, time):
        for module in self.get_traced_modules():
            module.update_signals(time)

    def set_data(self, data):
        self.data = data
        for module in self.get_traced_modules():
            module.set_data(data)


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
