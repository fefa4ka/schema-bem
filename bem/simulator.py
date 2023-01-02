import builtins
import io
import logging
from collections import defaultdict
from contextlib import redirect_stdout
from math import log

#from numpy.fft import fft
from PySpice.Unit import u_Degree, u_ms, u_s
from skidl import (KICAD, SPICE, Circuit, Net, search, set_backup_lib,
                   set_default_tool, subcircuit, reset)
from skidl.pyspice import *

from .base import Block
from .utils.logger import ERC_logger
from .utils.args import u

from pdb import set_trace as bp

libs = 'spice'


default_temperature = [-30, 0, 25] @ u_Degree

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
        circuit = builtins.default_circuit

        # Connect unused units to NC network
        # Needed for correct SPICE simulation
        units = circuit.units
        for unit in units:
            for block in units[unit]:
                part = block.instance.part()
                for pin in part.get_pins():
                    if len(pin.get_nets()) == 0:
                        pin & circuit.NC

        self.circuit = circuit.generate_netlist(libs=libs)

        print(self.circuit)
        # Grab ERC from logger
        erc = ERC_logger()
        builtins.default_circuit.ERC()
        self.ERC = erc.contents()

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
        measures = {}
        for temp in temperature or default_temperature:
            simulation = self.circuit.simulator(temperature=temp, nominal_temperature=temp)

            analysis = simulation.dc(**params)
            measures[u(temp)] = self.measures(analysis)

        return measures

    def ac(self, temperature=default_temperature, **params):
        measures = {}
        for temp in temperature or default_temperature:
            simulation = self.circuit.simulator(temperature=temp, nominal_temperature=temp)

            analysis = simulation.ac(**params)
            measures[str(temp)] = analysis

        return measures

    def volt_ampere(self, voltage_sweep, temperature=default_temperature, axis_x='V_input', axis_y='I_vvvs'):
        simulations = Simulate(self.block).dc({ 'VVVS': voltage_sweep }, temperature=temperature)
        chart = defaultdict(dict)
        for temp, simulation in simulations.items():
            label = '@ %s °C' % str(temp)
            for run in simulation:
                index = run['sweep']

                chart[index][axis_x] = run[axis_x]
                chart[index][label + ' ' + axis_y] = run[axis_y]

        sweep = list(chart.keys())

        sweep.sort()

        return [chart[index] for index in sweep]

    def volt_volt(self, voltage_sweep, temperature=default_temperature, axis_x='V_input', axis_y='V_output'):
        simulations = Simulate(self.block).dc({ 'VVVS': voltage_sweep }, temperature=temperature)
        chart = defaultdict(dict)
        for temp, simulation in simulations.items():
            label = '@ %s °C' % str(temp)
            for run in simulation:
                index = run['sweep']
                chart[index][axis_x] = run[axis_x]
                chart[index][axis_y] = run[axis_y]

        sweep = list(chart.keys())

        sweep.sort()

        return [chart[index] for index in sweep]

    def frequency(self, start_frequency, stop_frequency, temperature=default_temperature, **param):
        simulations = Simulate(self.block).ac(start_frequency=start_frequency, stop_frequency=stop_frequency, number_of_points=1000, variation='dec', temperature=temperature)

        # analys[temp][freq] = v_out / v_in
        chart = defaultdict(dict)
        for temp, simulation in simulations.items():
            label = '@ %s °C' % str(temp)
            for index, frequency in enumerate(simulation.frequency):
                V_in = simulation[self.block.input.name][index]
                V_out = simulation[self.block.output.name][index]
                # label += '@ %s' % str(frequency)
                # index = simulation['sweep']
                chart[index]['Frequency'] = float(frequency)
                chart[index][label + ' Gain'] = 20 * log(float(abs(V_out) / abs(V_in)), 10) if V_out and V_in else 0

        sweep = list(chart.keys())

        sweep.sort()

        return [chart[index] for index in sweep]

def set_spice_enviroment():
    Block.scope = []
    Block.refs = []
    set_backup_lib('.')
    builtins.SIMULATION = True
    builtins.SPICE = 'spice'

#    builtins.SPICE = 'SPICE'
    reset()

    scheme = Circuit()
    scheme.units = defaultdict(list)
    builtins.default_circuit.reset(init=True)
    del builtins.default_circuit
    builtins.default_circuit = scheme
    scheme.NC = Net('NC')
    builtins.NC = scheme.NC
