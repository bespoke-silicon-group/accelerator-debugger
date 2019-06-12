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
        self.value = value.lower()
        self.hex_str, self.int_val = self.val_to_hex()

    @property
    def as_int(self):
        return self.int_val

    @property
    def as_hex(self):
        return self.hex_str

    @property
    def as_str(self):
        return self.value

    def val_to_hex(self):
        hex_num = ""
        # Translate number in chunks of 4
        num_len = len(self.value)
        for i in range(0, num_len, 4):
            end_idx = min(i + 4, num_len)
            if i == 0:
                chunk_str = self.value[-(i + 4):]
            else:
                chunk_str = self.value[-(i + 4):-i]
            if 'x' in chunk_str:
                hex_num += 'x'
            elif 'z' in chunk_str:
                hex_num += 'z'
            else:
                hex_num = hex(int(chunk_str, 2))[2:] + hex_num
        try:
            int_val = int(hex_num, 16)
        except ValueError as e:
            int_val = None
        return ('0x' + hex_num, int_val)

    def __eq__(self, other):
        if isinstance(other, Value):
            str1, str2 = self.value, other.value
        else:
            if type(other) == str:
                if '0b' in other:
                    str1, str2  = self.as_str, other[2:]
                elif '0x' in other:
                    str1, str2 = self.as_hex[2:], other[2:]
                else:
                    raise RuntimeError("Need to prefix value with 0b or 0x")
            else: # Assumed to be an integer
                str1, str2 = self.value, bin(other)[2:]
        return all('x' in [c1,c2] or c1 == c2 for c1, c2 in zip(str1, str2))

    def __str__(self):
        return self.as_hex

    def __repr__(self):
        return str(self.as_int)

    def __hash__(self):
        if self.int_val is None:
            return 0
        return self.int_val


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

    def __repr__(self):
        return str(self) + " " + self.symbol


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

    def update(self, curr_time, step_time, num_steps):
        new_time = curr_time + step_time * num_steps
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal.symbol, new_time))

    def rupdate(self, curr_time, step_time, num_steps):
        new_time = curr_time - (step_time * num_steps)
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal.symbol, new_time))


class Memory(HWModule):
    """A memory traces when writes occur based on the enable signal.
    If a size is given, we allocated a memory of the given size,
    otherwise memory locations are allocated lazily when writes occur.
    The user can also specify segments of addresses that should be
    exclusively tracked and displayed.
    segments should be given as a list of individual address and
    (start_addr, end_addr) tuples, all as hex.
    show_signals sets whether address, data, and write_enable signals should
    be show (default False)
    """
    def __init__(self, module_name, addr, wdata, enable, enable_level,
                 segments=[], size=0, show_signals=False):
        HWModule.__init__(self, module_name, [addr, wdata, enable])
        self.size = size
        # If the user gave a size, we should allocate memory
        if self.size:
            self.memory = [(x, '0') for x in range(self.size)]
            self.memory = dict(self.memory)
        else:
            self.memory = {}
        self.segments = segments
        for i, segment in enumerate(self.segments):
            if isinstance(segment, tuple):
                self.segments[i] = (int(segment[0], 16), int(segment[1], 16))
            else:
                self.segments[i] = int(segment, 16)
        self.enable_level = bool(enable_level)
        self.show_signals = show_signals

    def addr_in_range(self, addr):
        """Check if an integer address is in one of the ranges given by the
        user"""
        if not self.segments:
            return True
        for segment in self.segments:
            if isinstance(segment, tuple):
                if segment[0] <= addr <= segment[1]:
                    return True
            else:
                if segment == addr:
                    return True
        return False

    def get_signal_dict(self):
        d = {}
        for signal in self.get_signals():
            short_name = signal.name.split('.')[-1]
            d[short_name] = signal.value
        d.update(self.memory)
        return AttrDict(d)

    @staticmethod
    def print_mem_table(seq, columns=2):
        table = ''
        col_height = len(seq) // columns
        for row in range(col_height):
            for col in range(columns):
                addr = (row * columns) + col
                val = seq[row + (col_height * col)]
                table += f" ({addr})={str(val)}".ljust(8)
            table += '\n'
        return table

    def __str__(self):
        desc = self.get_name() + ": "
        if self.show_signals:
            for signal in self.get_signals():
                desc += f"\n  {str(signal)}"
        if self.size and not self.segments:
            desc += "\n" + self.print_mem_table(self.memory, columns=3) + "\n"
        else:
            for addr in self.memory.keys():
                if self.addr_in_range(addr):
                    desc += f"\n   {addr}:{str(self.memory[addr])}"
        return desc

    def is_enable(self):
        en_val = bool(self.signals[2].value.as_int)
        return en_val == self.enable_level

    def write(self):
        mem_addr = self.signals[0].value.as_int
        if mem_addr is None or not self.addr_in_range(mem_addr):
            return
        if self.size:
            if mem_addr >= self.size:
                raise ValueError("Out of Bounds Memory access!\n")
        self.memory[mem_addr] = self.signals[1].value

    def write_if_en(self):
        if self.is_enable():
            self.write()

    def set_data(self, data):
        super(Memory, self).set_data(data)
        self.write_if_en()

    def step(self, curr_time, step_time):
        new_time = curr_time + step_time
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal.symbol, new_time))
        self.write_if_en()

    def update(self, curr_time, step_time, num_steps):
        enable = self.signals[2]
        end_time = curr_time + num_steps * step_time
        while curr_time < end_time:
            next_change = self.data.get_next_change(enable.symbol, curr_time)
            if next_change is None:
                return
            curr_time = next_change[0]
            enable.value = Value(next_change[1])
            if self.is_enable():
                # Update addr and data
                for sig in self.signals[:2]:
                    sig.value = Value(self.data.get_value(sig.symbol, curr_time))
                # Perform write
                self.write()

    def _get_last_write_value(self, curr_time, write_addr):
        """Get the last data written to write_addr strictly before curr_time"""
        assert isinstance(write_addr, int)
        enable = self.signals[2]
        addr = self.signals[0]
        wdata = self.signals[1]
        while curr_time > 0:
            prev_change = self.data.get_prev_change(enable.symbol, curr_time)
            if prev_change is None:
                return None
            change_time, change_val = prev_change
            change_addr = Value(self.data.get_value(addr.symbol, change_time))
            if change_addr.as_int == write_addr:
                return Value(self.data.get_value(wdata.symbol, change_time))
            curr_time = change_time
        return Value('xx')


    def rupdate(self, curr_time, step_time, num_steps):
        enable = self.signals[2]
        addr = self.signals[0]
        wdata = self.signals[1]
        new_time = curr_time - (step_time * num_steps)
        while new_time < curr_time:
            prev_change = self.data.get_prev_change(enable.symbol, curr_time)
            if prev_change is None:
                return
            curr_time = prev_change[0]
            enable.value = Value(prev_change[1])
            if new_time <= curr_time and self.is_enable():
                # Search back to find the last value written to current addr
                for sig in self.signals[:2]:
                    sig.value = Value(self.data.get_value(sig.symbol, curr_time))
                int_addr = self.signals[0].value.as_int
                # Search backwards to find the last write to given addr
                wdata.value = self._get_last_write_value(curr_time, int_addr)
                self.write()
            else:
                for sig in self.signals[:2]:
                    sig.value = Value(self.data.get_value(sig.symbol, new_time))

class HWModel(metaclass=abc.ABCMeta):
    def __init__(self):
        self.data = None
        self.time = 0
        self.end_time = None

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

    @property
    def step_time(self):
        raise NotImplementedError

    def get_end_time(self):
        return self.end_time

    def get_module(self, name):
        modules = self.get_traced_modules()
        req_module = [m for m in modules if m.get_name() == name]
        if not req_module:
            return None
        return req_module[0]

    def step(self):
        if self.sim_time >= self.end_time:
            return self.sim_time
        self.sim_time += self.step_time
        for module in self.get_traced_modules():
            module.step(self.sim_time, self.step_time)
        return self.sim_time

    def set_data(self, data):
        self.data = data
        self.end_time = data.get_endtime()
        for module in self.get_traced_modules():
            module.set_data(data)

    def update(self, num_steps, forward=True):
        end_time = num_steps * self.step_time + self.sim_time
        end_time = min(self.get_end_time(), end_time)
        num_steps = (end_time - self.sim_time) // self.step_time
        for module in self.get_traced_modules():
            module.update(self.sim_time, self.step_time, num_steps)
        self.sim_time = end_time
        return self.sim_time

    def rupdate(self, num_steps):
        end_time = self.sim_time - (num_steps * self.step_time)
        end_time = max(0, end_time)
        num_steps = (self.sim_time - end_time) // self.step_time
        for module in self.get_traced_modules():
            module.rupdate(self.sim_time, self.step_time, num_steps)
        self.sim_time = end_time
        return self.sim_time
