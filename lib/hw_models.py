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


class HWModule(metaclass=abc.ABCMeta):
    """ Signals are tuples of (global_symbol, name_in_module, value) """
    def get_signal_names(self):
        return self.signal_names

    def get_signals(self):
        return self.signals

    def get_name(self):
        return self.name

    def set_data(self, data):
        self.data = data
        for signal in self.signal_names:
            symbol = self.data.get_symbol(signal)
            value = self.data.get_value(symbol, 0)
            self.signals.append(Signal(symbol, signal, value))

    def __str__(self):
        raise NotImplementedError

    def update_signals(self, time):
        raise NotImplementedError


class BasicModule(HWModule):
    def __init__(self, module_name, signal_names):
        self.signal_names = signal_names
        self.signals = []
        self.name = module_name
        self.data = None

    def __str__(self):
        desc = self.get_name() + ": "
        for signal in self.get_signals():
            desc += f"\n\t{str(signal)}"
        return desc

    def update_signals(self, curr_time, steps, step_time):
        new_time = curr_time + steps * step_time
        for signal in self.get_signals():
            signal.value = self.data.get_value(signal.symbol, new_time)


class LazyMemory(HWModule):
    """A LazyMemory module tracks the accesses to a memory, but only
    after writes has occurred. It assumes that memory is initalized to 'x'"""
    def __init__(self, module_name, addr, wdata, enable, enable_level):
        self.signal_names = [addr, wdata, enable]
        self.name = module_name
        self.signals = []
        self.memory = {}
        self.enable_level = enable_level
        self.data = None

    def __str__(self):
        desc = self.get_name() + ": "
        for signal in self.get_signals():
            desc += f"\n\t{str(signal)}"
        for addr in self.memory:
            desc += f"\n\t\t{addr}: {self.memory[addr]}"
        return desc

    def write_if_en(self):
        if bool(self.signals[2].value) == self.enable_level:
            self.memory[self.signals[0].value] = self.signals[1].value

    def set_data(self, data):
        super(LazyMemory, self).set_data(data)
        self.write_if_en()

    def update_signals(self, curr_time, steps, step_time):
        new_time = curr_time
        for step in range(steps):
            new_time += step_time
            for signal in self.get_signals():
                signal.value = self.data.get_value(signal.symbol, new_time)
            self.write_if_en()


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

    def update(self, curr_time, steps):
        print(curr_time, steps)
        step_time = self.get_step_time()
        for module in self.get_traced_modules():
            module.update_signals(curr_time, steps, step_time)
        return curr_time + steps * step_time

    def set_data(self, data):
        self.data = data
        for module in self.get_traced_modules():
            module.set_data(data)
