#! /usr/bin/env python3

import abc

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Value():
    """Values in VCD can have don't cares or high-impedence values, this
    lets us equate value with and without don't cares, as well as translate
    number into integers that we can"""
    def __init__(self, value):
        self.val_str = value.lower()
        self.value = value
        self.hex_str = None

    def val_to_hex(self):
        rev_num = self.value[::-1]
        hex_num = ""
        # Translate number in chunks of 4
        num_len = len(self.value)
        for i in range(0, num_len, 4):
            end_idx = min(i + 4, num_len)
            chunk_str = self.value[i:end_idx]
            if 'x' in chunk_str:
                hex_num += 'x'
            elif 'z' in chunk_str:
                hex_num += 'z'
            else:
                hex_num = hex(int(chunk_str, 2))[2:]
        return hex_num

    def __eq__(self, other):
        if self.hex_str is None:
            self.hex_str = self.val_to_hex()

        if isinstance(other, Value):
            str1, str2 = self.val_str, other.val_str
        else:
            if type(other) == str:
                if '0b' in other:
                    str1, str2  = self.val_str, other[2:]
                elif '0x' in other:
                    str1, str2 = self.hex_str, other[2:]
                else:
                    raise RuntimeError("Need to prefix value with 0b or 0x")
            else: # Assumed to be an integer
                str1, str2 = self.val_str, bin(other)[2:]
        return all('x' in [c1,c2] or c1 == c2 for c1, c2 in zip(str1, str2))

    def __str__(self):
        if self.hex_str is None:
            self.hex_str = self.val_to_hex()
        return '0x' + self.hex_str

    def __hash__(self):
        return hash(self.val_str)


class Signal():
    """Signals are compsed of the VCD symbol that represents the signal,
    the name of the signal in the HW module that's it's part of, and
    its current value"""
    def __init__(self, symbol, name, value):
        self.symbol = symbol
        self.name = name
        self.value = Value(value)

    def __str__(self):
        short_name = self.name.split('.')[-1]
        return f"{short_name}: {str(self.value)}"


class HWModule(metaclass=abc.ABCMeta):
    """ Signals are tuples of (global_symbol, name_in_module, value) """
    def __init__(self, module_name, signal_names):
        self.signal_names = signal_names
        self.name = module_name
        self.signals = []
        self.data = None

    def get_signal_names(self):
        return self.signal_names

    def get_signals(self):
        return self.signals

    def get_signal_dict(self):
        raise NotImplementedError

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

    def step(self, curr_time, step_time):
        raise NotImplementedError


class BasicModule(HWModule):
    def __str__(self):
        desc = self.get_name() + ": "
        for signal in self.get_signals():
            desc += f"\n    {str(signal)}"
        return desc

    def get_signal_dict(self):
        d = {}
        for signal in self.get_signals():
            short_name = signal.name.split('.')[-1]
            d[short_name] = signal.value
        return AttrDict(d)

    def step(self, curr_time, step_time):
        new_time = curr_time + step_time
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal.symbol, new_time))


class Memory(HWModule):
    """A memory traces when writes occur based on the enable signal.
    If a size is given, we allocated a memory of the given size,
    otherwise memory locations are allocated lazily when writes occur"""
    def __init__(self, module_name, addr, wdata, enable, enable_level, size=0):
        HWModule.__init__(self, module_name, [addr, wdata, enable])
        self.size = size
        # If the user gave a size, we should allocate memory
        if self.size:
            self.memory = ['0'] * self.size
        else:
            self.memory = {}
        self.enable_level = enable_level

    def get_signal_dict(self):
        d = {}
        for signal in self.get_signals():
            short_name = signal.name.split('.')[-1]
            d[short_name] = signal.value
        d['mem'] = self.memory
        return AttrDict(d)

    @staticmethod
    def print_mem_table(seq, columns=2):
        table = ''
        col_height = len(seq) // columns
        for row in range(col_height):
            for col in range(columns):
                addr = (row * columns) + col
                val = seq[row + (col_height * col)]
                table += f" ({addr})={str(val)}".ljust(16)
            table += '\n'
        return table

    def __str__(self):
        desc = self.get_name() + ": "
        for signal in self.get_signals():
            desc += f"\n    {str(signal)}"
        desc += "\nmem:\n"
        if self.size:
            desc += self.print_mem_table(self.memory, columns=3) + "\n"
        else:
            for addr, value in enumerate(self.memory):
                desc += f"    {addr}:{str(value)}\n"
        return desc

    def write_if_en(self):
        en_str = self.signals[2].value.val_str
        en_val = int(en_str) if 'x' not in en_str else not self.enable_level
        if en_val == int(self.enable_level):
            mem_addr = self.signals[0].value
            if self.size:
                if 'x' in mem_addr:
                    return
                mem_addr = int(mem_addr, 2)
            self.memory[mem_addr] = self.signals[1].value

    def set_data(self, data):
        super(Memory, self).set_data(data)
        self.write_if_en()

    def step(self, curr_time, step_time):
        new_time = curr_time + step_time
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal.symbol, new_time))
        self.write_if_en()


class HWModel(metaclass=abc.ABCMeta):
    def __init__(self):
        self.data = None
        self.time = 0

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

    @property
    def sim_time(self):
        return self.time

    @sim_time.setter
    def sim_time(self, value):
        self.time = value

    @abc.abstractmethod
    def get_traced_modules(self):
        raise NotImplementedError

    @abc.abstractmethod
    def get_step_time(self):
        raise NotImplementedError

    def get_module(self, name):
        modules = self.get_traced_modules()
        req_module = [m for m in modules if m.get_name() == name]
        if not req_module:
            return None
        return req_module[0]

    def step(self):
        self.sim_time += self.get_step_time()
        for module in self.get_traced_modules():
            module.step(self.sim_time, self.get_step_time())
        return self.sim_time

    def set_data(self, data):
        self.data = data
        for module in self.get_traced_modules():
            module.set_data(data)
