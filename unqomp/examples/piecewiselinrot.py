
# Adapted from https://qiskit.org/documentation/_modules/qiskit/circuit/library/arithmetic/piecewise_linear_pauli_rotations.html#PiecewiseLinearPauliRotations

"""Piecewise-linearly-controlled rotation."""
from typing import List, Optional
from qiskit.circuit import Gate
import numpy as np

from qiskit.circuit import QuantumRegister, QuantumCircuit
from qiskit.circuit.exceptions import CircuitError

from qiskit.circuit.library.arithmetic.linear_pauli_rotations import LinearPauliRotations

from unqomp.examples.intergercomparator import makeIntegerComparator
from unqomp.ancillaallocation import AncillaRegister, AncillaCircuit



# Define a custom Controlled-Y gate that does not decompose
class CustomCRYGate(Gate):
    def __init__(self):
        super().__init__('custom_cry', 2, [])

    def _define(self):
        # Leave the definition empty to prevent decomposition
        self.definition = None


def _contains_zero_breakpoint(breakpoints):
    return np.isclose(0, breakpoints[0])



def makesPLR(num_state_qubits, breakpoints, slopes, offsets):
    qr_state = QuantumRegister(num_state_qubits, name='state')
    qr_target = QuantumRegister(1, name='target')
    circuit = AncillaCircuit(qr_state, qr_target)

    mapped_slopes = np.zeros_like(slopes)
    for i, slope in enumerate(slopes):
        mapped_slopes[i] = slope - sum(mapped_slopes[:i])

    mapped_offsets = np.zeros_like(offsets)
    for i, (offset, slope, point) in enumerate(zip(offsets, slopes, breakpoints)):
        print("\t\t", offset, slope * point)
        mapped_offsets[i] = offset - slope * point - sum(mapped_offsets[:i])
    print(mapped_offsets)
    basis = 'Y'
    # mapped_offsets = [-1 for x in range(len(mapped_offsets))]
    print("mapped slope and offset is ", mapped_slopes, mapped_offsets)
    # apply comparators and controlled linear rotations
    for i, point in enumerate(breakpoints):
        if i == 0 and _contains_zero_breakpoint(breakpoints):
            # apply rotation
            print("A")
            lin_r = LinearPauliRotations(num_state_qubits=num_state_qubits,
                                         slope=mapped_slopes[i],
                                         offset=mapped_offsets[i], basis = 'Y')
            circuit.append(lin_r.to_gate(), qr_state[:] + [qr_target])

        else:
            print("B")
            comp_ancilla = circuit.new_ancilla_register(1, name = 'ac' + str(i))
            print(" =========== ")
            temp = makeIntegerComparator(num_state_qubits, point).to_ancilla_gate()
            print("We get TEMP HERE")
            
            circuit.append(makeIntegerComparator(num_state_qubits, point).to_ancilla_gate(), [*qr_state[:], comp_ancilla[0]])
             
            # apply controlled rotation
            lin_r = LinearPauliRotations(num_state_qubits=num_state_qubits,
                                         slope=mapped_slopes[i],
                                         offset=mapped_offsets[i],
                                         basis=basis)

            print("we get LINEAR ROTATINS HERE")
            # Replace all CY gates with CustomCYGate
            for idx, (instruction, qubits, clbits) in enumerate(lin_r.data):
               lin_r.data[idx][0]._definition = None
               #print(instruction, vars(instruction))
               # if instruction.name == '':
               #     # Remove the original CY gate and add the custom one
               #     print("rep")
               #     lin_r.data[idx] = (CustomCRYGate(), qubits, clbits)
               print(lin_r)
            #print(lin_r.decompose().decompose())
            #print("definitions ", lin_r.to_gate().control()._definition)
            #print("Lin2")
            #print(lin_r)
            #print(lin_r.to_gate().control())
            print("ADD A CONTROL GATE")
            temp = lin_r.to_gate().control()
            print("CONTROL GATE CREATED")
            circuit.append(temp, [comp_ancilla[0]] + qr_state[:] + [qr_target])
            print("CONTROL GATE ADDED")
        #print("i done")
    # print("+++++++++++++++")
    return circuit
