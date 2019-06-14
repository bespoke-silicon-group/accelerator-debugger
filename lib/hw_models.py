#! /usr/bin/env python3

from collections import namedtuple

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
        except ValueError:
            int_val = None
        return ('0x' + hex_num, int_val)

    def __eq__(self, other):
        if isinstance(other, Value):
            str1, str2 = self.value, other.value
        else:
            if isinstance(other, str):
                if '0b' in other:
                    str1, str2 = self.as_str, other[2:]
                elif '0x' in other:
                    str1, str2 = self.as_hex[2:], other[2:]
                else:
                    raise RuntimeError("Need to prefix value with 0b or 0x")
            else: # Assumed to be an integer
                str1, str2 = self.value, bin(other)[2:]
        return all('x' in [c1, c2] or c1 == c2 for c1, c2 in zip(str1, str2))

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
    def __init__(self, sig_name, vcd_data):
        self._symbol = vcd_data.get_symbol(sig_name)
        self.name = sig_name
        self.value = Value(vcd_data.get_value(self, 0))

    def __str__(self):
        short_name = self.name.split('.')[-1]
        return f"{short_name}: {str(self.value)}"

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, value):
        self._symbol = value

    def __repr__(self):
        return str(self) + " " + self.symbol


class HWModule():
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
        for sig_name in self.signal_names:
            self.signals.append(Signal(sig_name, data))

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
        signal_dict = {}
        for signal in self.get_signals():
            short_name = signal.name.split('.')[-1]
            signal_dict[short_name] = signal.value
        return AttrDict(signal_dict)

    def step(self, curr_time, step_time):
        new_time = curr_time + step_time
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal, new_time))

    def update(self, curr_time, step_time, num_steps):
        new_time = curr_time + step_time * num_steps
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal, new_time))

    def rupdate(self, curr_time, step_time, num_steps):
        new_time = curr_time - (step_time * num_steps)
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal, new_time))


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
                 segments=None, size=0, show_signals=False):
        HWModule.__init__(self, module_name, [addr, wdata, enable])
        self.size = size
        # If the user gave a size, we should allocate memory
        if self.size:
            self.memory = [(x, '0') for x in range(self.size)]
            self.memory = dict(self.memory)
        else:
            self.memory = {}
        self.enable_level = bool(enable_level)
        self.show_signals = show_signals
        self.segments = segments
        if segments is None:
            return
        Segment = namedtuple("Segment", 'start end')
        for i, segment in enumerate(self.segments):
            if isinstance(segment, tuple):
                start, end = (int(segment[0], 16), int(segment[1], 16))
            else:
                start, end = (int(segment, 16), int(segment, 16))
            self.segments[i] = Segment(start, end)

    @property
    def addr(self):
        return self.signals[0]

    @property
    def wdata(self):
        return self.signals[1]

    @property
    def enable(self):
        return self.signals[2]

    def addr_in_range(self, addr):
        """Check if an integer address is in one of the ranges given by the
        user"""
        if not self.segments:
            return True
        for segment in self.segments:
            if segment.start <= addr <= segment.end:
                return True
        return False

    def get_signal_dict(self):
        signal_dict = {}
        for signal in self.get_signals():
            short_name = signal.name.split('.')[-1]
            signal_dict[short_name] = signal.value
        signal_dict.update(self.memory)
        return AttrDict(signal_dict)

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
        en_val = bool(self.enable.value.as_int)
        return en_val == self.enable_level

    def write(self):
        mem_addr = self.addr.value.as_int
        if mem_addr is None or not self.addr_in_range(mem_addr):
            return
        if self.size:
            if mem_addr >= self.size:
                raise ValueError("Out of Bounds Memory access!\n")
        self.memory[mem_addr] = self.wdata.value

    def write_if_en(self):
        if self.is_enable():
            self.write()

    def set_data(self, data):
        super(Memory, self).set_data(data)
        self.write_if_en()

    def step(self, curr_time, step_time):
        new_time = curr_time + step_time
        for signal in self.get_signals():
            signal.value = Value(self.data.get_value(signal, new_time))
        self.write_if_en()

    def update(self, curr_time, step_time, num_steps):
        end_time = curr_time + num_steps * step_time
        while curr_time < end_time:
            next_change = self.data.get_next_change(self.enable, curr_time)
            if next_change is None:
                return
            curr_time = next_change.time
            self.enable.value = Value(next_change.val)
            if self.is_enable():
                # Update addr and data
                self.addr.value = Value(self.data.get_value(self.addr,
                                                            curr_time))
                self.wdata.value = Value(self.data.get_value(self.wdata,
                                                             curr_time))
                # Perform write
                self.write()

    def _get_last_write_value(self, curr_time, write_addr):
        """Get the last data written to write_addr strictly before curr_time"""
        assert isinstance(write_addr, int)
        while curr_time > 0:
            prev_change = self.data.get_prev_change(self.enable, curr_time)
            if prev_change is None:
                return None
            change_time = prev_change[0]
            change_addr = Value(self.data.get_value(self.addr, change_time))
            if change_addr.as_int == write_addr:
                return Value(self.data.get_value(self.wdata, change_time))
            curr_time = change_time
        return Value('xx')


    def rupdate(self, curr_time, step_time, num_steps):
        new_time = curr_time - (step_time * num_steps)
        while new_time < curr_time:
            prev_change = self.data.get_prev_change(self.enable, curr_time)
            if prev_change is None:
                return
            curr_time = prev_change.time
            self.enable.value = Value(prev_change.val)
            if new_time <= curr_time and self.is_enable():
                # Search back to find the last value written to current addr
                for sig in self.signals[:2]:
                    sig.value = Value(self.data.get_value(sig, curr_time))
                int_addr = self.addr.value.as_int
                # Search backwards to find the last write to given addr
                self.wdata.value = self._get_last_write_value(curr_time,
                                                              int_addr)
                self.write()
            else:
                for sig in self.signals[:2]:
                    sig.value = Value(self.data.get_value(sig, new_time))

class HWModel():
    def __init__(self, step_time):
        self.data = None
        self.time = 0
        self.end_time = None
        self._step_time = step_time
        self.modules = []

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

    def add_module(self, module):
        self.modules.append(module)

    @property
    def sim_time(self):
        return self.time

    @sim_time.setter
    def sim_time(self, value):
        self.time = value

    def get_traced_modules(self):
        return self.modules

    @property
    def step_time(self):
        return self._step_time

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

    def update(self, num_steps):
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
