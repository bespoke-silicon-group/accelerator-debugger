#! /usr/bin/env python3

"""Back-end for the debugger. Hardware Models (DebugModel) are composed of
Hardware Modules (DebugModule), which are composed of Signals, which have a
Value"""

from collections import namedtuple


class AttrDict(dict):
    """Dictionary where values can be accessed via dict.key_name"""
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Value():
    """Values in VCD can have don't cares or high-impedence values, this
    lets us equate value with and without don't cares, as well as translate
    number into integers that we can"""
    def __init__(self, value):
        self.value = value.lower()
        self.hex_str, self.int_val = self._val_to_hex()

    @property
    def as_int(self):
        """Return the integer value, None if the Value doesn't have an integer
        representation"""
        return self.int_val

    @property
    def as_hex(self):
        """Return the hexadecimal representation of this Value"""
        return self.hex_str

    @property
    def as_str(self):
        """Returns the VCD string representation of this Value"""
        return self.value

    def _val_to_hex(self):
        """Generate the hexadecimal and integer representations of this
        Value"""
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
            else:  # Assumed to be an integer
                str1, str2 = self.value, bin(other)[2:]
        return all('x' in [c1, c2] or c1 == c2 for c1, c2 in zip(str1, str2))

    def __str__(self):
        if self.int_val is None:
            return "x"
        return self.as_hex

    def __repr__(self):
        return str(self.as_int)

    def __hash__(self):
        if self.int_val is None:
            return 0
        return self.int_val


class Signal():
    """Signals are compsed of the VCD symbol that represents the signal,
    the name of the signal in the DebugModule that's it's part of, and
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
        """Get the VCD symbol corresponding to this signal"""
        return self._symbol

    @symbol.setter
    def symbol(self, value):
        self._symbol = value

    def __repr__(self):
        return str(self) + " " + self.symbol


class DebugModule():
    """ Signals are tuples of (global_symbol, name_in_module, value) """
    def __init__(self, module_name, signal_names):
        self._signal_names = signal_names
        self._name = module_name
        self._signals = []
        self.data = None

    @property
    def signal_names(self):
        """The names of signals tracked by this Module"""
        return self._signal_names

    @property
    def signals(self):
        """The signals tracked by this Module"""
        return self._signals

    @property
    def signal_dict(self):
        """Get a dictionary of signal_name: value"""
        raise NotImplementedError

    @property
    def name(self):
        """The name of this module"""
        return self._name

    def set_data(self, data):
        """Set the VCD data that this module should use as a backend"""
        self.data = data
        for sig_name in self.signal_names:
            self._signals.append(Signal(sig_name, data))

    def __str__(self):
        raise NotImplementedError

    def edge(self, curr_time, edge_time):
        """Move the module forward one clock edge in time"""
        raise NotImplementedError

    def update(self, curr_time, edge_time, num_edges):
        """Update this module to curr_time + edge_time * num_edges"""
        raise NotImplementedError

    def rupdate(self, curr_time, edge_time, num_edges):
        """Update this module to curr_time - edge_time * num_edges"""
        raise NotImplementedError


class BasicModule(DebugModule):
    """A module with plain signals that don't have side effects (i.e. not
    memory signals"""
    def __str__(self):
        desc = self.name + ": "
        for signal in self.signals:
            desc += f"\n    {str(signal)}"
        return desc

    @property
    def signal_dict(self):
        signal_dict = {}
        for signal in self.signals:
            short_name = signal.name.split('.')[-1].split('[')[0]
            signal_dict[short_name] = signal.value
        return AttrDict(signal_dict)

    def edge(self, curr_time, edge_time):
        new_time = curr_time + edge_time
        for signal in self.signals:
            signal.value = Value(self.data.get_value(signal, new_time))

    def update(self, curr_time, edge_time, num_edges):
        new_time = curr_time + edge_time * num_edges
        for signal in self.signals:
            signal.value = Value(self.data.get_value(signal, new_time))

    def rupdate(self, curr_time, edge_time, num_edges):
        new_time = curr_time - (edge_time * num_edges)
        for signal in self.signals:
            signal.value = Value(self.data.get_value(signal, new_time))


class Memory(DebugModule):
    """A memory traces when writes occur based on the enable signal.

    If a size is given, we allocated a memory of the given size,
    otherwise memory locations are allocated lazily when writes occur.

    The user can also specify segments of addresses that should be
    exclusively tracked and displayed.

    segments should be given as a list of individual address and
    (start_addr, end_addr) tuples, all as hex.

    show_signals sets whether address, data, and write_enable signals should
    be shown in the display (default False)
    """
    def __init__(self, module_name, addr, wdata, enable, enable_level,
                 segments=None, size=0, show_signals=False):
        DebugModule.__init__(self, module_name, [addr, wdata, enable])
        self.size = size
        # If the user gave a size, we should allocate memory
        if self.size:
            self.memory = [(x, 'x') for x in range(self.size)]
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
        """The address signal for this memory"""
        return self.signals[0]

    @property
    def wdata(self):
        """The write data signal for this memory"""
        return self.signals[1]

    @property
    def enable(self):
        """The enable signal for this memory"""
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

    @property
    def signal_dict(self):
        signal_dict = {}
        for signal in self.signals:
            short_name = signal.name.split('.')[-1]
            signal_dict[short_name] = signal.value
        signal_dict.update(self.memory)
        return AttrDict(signal_dict)

    @staticmethod
    def print_mem_table(seq, columns=2):
        """Print a table of memory values as a table with a fixed number of
        columns"""
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
        desc = self.name + ": "
        if self.show_signals:
            for signal in self.signals:
                desc += f"\n  {str(signal)}"
        if self.size and not self.segments:
            desc += "\n" + self.print_mem_table(self.memory, columns=3) + "\n"
        else:
            for addr in self.memory.keys():
                if self.addr_in_range(addr):
                    desc += f"\n   {addr}:{str(self.memory[addr])}"
        return desc

    def is_enable(self):
        """Check if the enable signal is asserted"""
        en_val = bool(self.enable.value.as_int)
        return en_val == self.enable_level

    def write(self):
        """Perform a write of the current value of wdata to the current value
        of addr"""
        mem_addr = self.addr.value.as_int
        if mem_addr is None or not self.addr_in_range(mem_addr):
            return
        if self.size:
            if mem_addr >= self.size:
                raise ValueError("Out of Bounds Memory access!\n")
        self.memory[mem_addr] = self.wdata.value

    def set_data(self, data):
        super(Memory, self).set_data(data)
        if self.is_enable():
            self.write()

    def edge(self, curr_time, edge_time):
        new_time = curr_time + edge_time
        for signal in self.signals:
            signal.value = Value(self.data.get_value(signal, new_time))
        if self.is_enable():
            self.write()

    def update(self, curr_time, edge_time, num_edges):
        end_time = curr_time + num_edges * edge_time
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
        return Value('x')

    def rupdate(self, curr_time, edge_time, num_edges):
        new_time = curr_time - (edge_time * num_edges)
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


class Core(DebugModule):
    def __init__(self, module_name, pc, other_signals=None):
        if other_signals is None:
            other_signals = []
        DebugModule.__init__(self, module_name, [pc] + other_signals)

    @property
    def pc(self):
        """The PC signal for this Core"""
        return self.signals[0]

    @property
    def signal_dict(self):
        pass

    def __str__(self):
        pass

    def edge(self, curr_time, edge_time):
        pass

    def update(self, curr_time, edge_time, num_edges):
        pass

    def rupdate(self, curr_time, edge_time, num_edges):
        pass


class DebugModel():
    """Hardware Models compose Hardware Module, which contain signals. This
    constitutes a simulation platform for debugging"""
    def __init__(self, edge_time):
        self.data = None
        self.time = 0
        self.end_time = None
        self._edge_time = edge_time
        self._modules = []

    @property
    def signals(self):
        """The Signals that the Model is tracking"""
        _signals = []
        for module in self.modules:
            _signals.extend(module.signals)
        return _signals

    @property
    def signal_names(self):
        """The names of the Signals that this Model is tracking"""
        names = []
        for module in self.modules:
            names.extend(module.signal_names)
        return names

    def add_module(self, module):
        """Add a module to the Model"""
        self.modules.append(module)

    @property
    def sim_time(self):
        """The current simulation time"""
        return self.time

    @sim_time.setter
    def sim_time(self, value):
        self.time = value

    @property
    def modules(self):
        """The modules contained within this model"""
        return self._modules

    @property
    def edge_time(self):
        """The edge increment for this model"""
        return self._edge_time

    def get_end_time(self):
        """The end time of simulation for this model"""
        return self.end_time

    def get_module(self, name):
        """Get a module contained within this model with the given name"""
        modules = self.modules
        req_module = [m for m in modules if m.name == name]
        if not req_module:
            return None
        return req_module[0]

    def edge(self):
        """Move the model forward by one clock edge"""
        if self.sim_time >= self.end_time:
            return self.sim_time
        self.sim_time += self.edge_time
        for module in self.modules:
            module.edge(self.sim_time, self.edge_time)
        return self.sim_time

    def set_data(self, data):
        """Set the VCD data that this model should use as a backing"""
        self.data = data
        self.end_time = data.get_endtime()
        for module in self.modules:
            module.set_data(data)

    def update(self, num_edges):
        """Updated this model by moving forward a given number of clock
        edges"""
        end_time = num_edges * self.edge_time + self.sim_time
        end_time = min(self.get_end_time(), end_time)
        num_edges = (end_time - self.sim_time) // self.edge_time
        for module in self.modules:
            module.update(self.sim_time, self.edge_time, num_edges)
        self.sim_time = end_time
        return self.sim_time

    def rupdate(self, num_edges):
        """Updated this model by moving backward a given number of clock
        edges"""
        end_time = self.sim_time - (num_edges * self.edge_time)
        end_time = max(0, end_time)
        num_edges = (self.sim_time - end_time) // self.edge_time
        for module in self.modules:
            module.rupdate(self.sim_time, self.edge_time, num_edges)
        self.sim_time = end_time
        return self.sim_time
