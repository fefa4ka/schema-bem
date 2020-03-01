import io
from contextlib import redirect_stdout
#from numpy.fft import fft
from PySpice.Unit import u_ms, u_s
from skidl import (KICAD, SPICE, Circuit, Net, search, set_default_tool, set_backup_lib,
                   subcircuit)

from .base import Block
from .util import u

import builtins

libs = ['./spice/']

import logging
import collections

from PySpice.Unit import u_Degree
default_temperature = [-30, 0, 25] @ u_Degree

class TailLogHandler(logging.Handler):
    def __init__(self, log_queue):
        logging.Handler.__init__(self)
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.append(self.format(record))


class TailLogger(object):
    def __init__(self, maxlen):
        self._log_queue = collections.deque(maxlen=maxlen)
        self._log_handler = TailLogHandler(self._log_queue)

    def contents(self):
        return '\n'.join(self._log_queue)

    @property
    def log_handler(self):
        return self._log_handler


class Simulate:
    block = None
    circuit = None
    simulation = None
    node = None

    SIMULATE = False
    spice_params = {}

    def __init__(self, block, libs=libs):
        self.block = block

        from skidl.tools.spice import node
        self.circuit = builtins.default_circuit.generate_netlist(libs=libs)

        # Grab ERC from logger 
        erc = logging.getLogger('ERC_Logger')
        tail = TailLogger(10)
        log_handler = tail.log_handler
        for handler in erc.handlers[:]:
            erc.removeHandler(handler)

        erc.addHandler(log_handler)
        builtins.default_circuit.ERC()
        self.ERC = tail.contents()
        print(self.circuit)

        self.node = node

    def measures(self, analysis):
        index_field = None
        index = None


        if hasattr(analysis, 'time'):
            index_field = 'time'
            index = analysis.time
        elif hasattr(analysis, 'frequency'):
            index_field = 'frequency'
            index = analysis.frequency
        else:
            index_field = 'sweep'
            index = analysis.sweep

        pins = self.block.get_pins().keys()

        current_branches = analysis.branches.keys()

        voltage = {}
        for pin in pins:
            try:
                net = getattr(self.block, pin)
                if net and pin != 'gnd' and net != self.block.gnd:
                    node = self.node(net)
                    voltage[pin] = analysis[node]
            except:
                pass

        current = {}
        for branch in current_branches:
            current[branch] = -analysis[branch]

        # voltage_fft = {}
        # for key in voltage.keys():
        #     voltage[key] = fft(voltage[key])


        data = []
        for index, entity in enumerate(index):
            entry = {
                index_field: entity.value * entity.scale
            }

            for key in voltage.keys():
                entry['V_' + key] = u(voltage[key][index])

            for key in current.keys():
                if key.find('.') == -1:
                    entry['I_' + key] = u(current[key][index])

            data.append(entry)

        return data


    def transient(self, step_time=0.01 @ u_ms, end_time=200 @ u_ms):
        self.simulation = self.circuit.simulator()
        analysis = self.simulation.transient(step_time=step_time, end_time=end_time)

        return self.measures(analysis)

    def dc(self, params, temperature=default_temperature):
        pins = self.block.get_pins().keys()
        measures = {}
        for temp in temperature or default_temperature:
            simulation = self.circuit.simulator(temperature=temp, nominal_temperature=temp)

            analysis = simulation.dc(**params)
            measures[u(temp)] = self.measures(analysis)

        return measures

    def ac(self, temperature=default_temperature, **params):
        pins = self.block.get_pins().keys()
        measures = {}
        for temp in temperature or default_temperature:
            simulation = self.circuit.simulator(temperature=temp, nominal_temperature=temp)
            analysis = simulation.ac(**params)
            measures[str(temp)] = analysis

        return measures


def set_spice_enviroment():
    set_backup_lib('.')
    set_default_tool(SPICE)
    builtins.SIMULATION = True

    scheme = Circuit()
    builtins.default_circuit.reset(init=True)
    del builtins.default_circuit
    builtins.default_circuit = scheme
    builtins.NC = scheme.NC
