import cmath
from qiskit.converters import circuit_to_dag # transpiler
import pydot
from qiskit.visualization import dag_drawer
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit import QuantumRegister, Qubit, Instruction
# from qiskit.circuit.library import H, CX, CCX
import math
from qiskit.dagcircuit import DAGCircuit


def decompose_mcx_with_ancilla(circuit, controls, target, ancillas, direction=None):
    """
    Decomposes an `mcx` gate with more than 3 controls using ancilla qubits.

    Args:
        circuit (QuantumCircuit): The circuit to apply the decomposition.
        controls (list): List of control qubits.
        target (Qubit): The target qubit for the `mcx` gate.
        ancillas (AncillaRegister): The ancilla qubits to use for decomposition.
    """
    num_controls = len(controls)
    if num_controls == 2:
        # Base case: Use a Toffoli gate (ccx) for 3 controls
        circuit.ccx(controls[0], controls[1], target)
    else:
        if num_controls % 2 == 0:
            if direction == "left" or direction is None:
                decompose_mcx_with_ancilla(circuit, controls[:len(controls)//2], ancillas[0], ancillas[2:], direction="left")
                decompose_mcx_with_ancilla(circuit, controls[len(controls)//2:], ancillas[1], ancillas[2:], direction="left")
            decompose_mcx_with_ancilla(circuit, [ancillas[0], ancillas[1]], target, None)
            if direction == "right" or direction is None:
                decompose_mcx_with_ancilla(circuit, controls[:len(controls)//2], ancillas[0], ancillas[2:], direction="right")
                decompose_mcx_with_ancilla(circuit, controls[len(controls)//2:], ancillas[1], ancillas[2:], direction="right")
        else:
            # Decompose using ancilla
            ancilla = ancillas[0]

            # Apply a series of Toffoli gates, using ancilla to reduce control count
            circuit.ccx(controls[0], controls[1], ancilla)
        
            # Recursively decompose remaining controls
            decompose_mcx_with_ancilla(circuit, [ancilla, *controls[2:]], target, ancillas[1:])

            # Reapply Toffoli gate to clean up ancilla
            circuit.ccx(controls[0], controls[1], ancilla)


def cczConvertor(circuit):
    num_qubits = circuit.num_qubits
    new_qreg = QuantumRegister(num_qubits, 'q')
    new_circ = QuantumCircuit(new_qreg)
    qubit_map = {old_qbit: new_qreg[idx] for idx, old_qbit in enumerate(circuit.qubits)}
    for gate in circuit.data:
        if len(gate[1]) == 3:
            new_operands = [qubit_map[x] for x in gate[1]]
            new_circ.h(new_operands[2])
            new_circ.ccx(new_operands[0], new_operands[1], new_operands[2])
            new_circ.h(new_operands[2])
    
        else:
            new_operands = [qubit_map[x] for x in gate[1]]
            new_circ.append(gate[0], new_operands)
    return new_circ


def qasmConvertor(circuit, path=None):
    # Step 2: Create a new quantum register with the same number of qubits, but different names
    num_qubits = circuit.num_qubits
    new_qubits = [0]
    for gate in circuit.data:
        if len(gate[1]) > 3:
            new_qubits.append(len(gate[1])-3)
    new_qreg = QuantumRegister(num_qubits + max(new_qubits), 'q')  # New qubits with different names
    ancillas = new_qreg[num_qubits:]
    # print("qubit info ", num_qubits, "qubits :", max(new_qubits), "new registers: ", len(new_qreg), " ancillas : ", len(ancillas))
    new_circ = QuantumCircuit(new_qreg)
    qubit_map = {old_qbit: new_qreg[idx] for idx, old_qbit in enumerate(circuit.qubits)}
    # Step 3: Copy the operations, mapping the old qubits to the new qubits
    for gate in circuit.data:
        if len(gate[1]) > 3:
            new_operands = [qubit_map[x] for x in gate[1]]
            # print(gate[0])
            decompose_mcx_with_ancilla(new_circ, new_operands[:-1], new_operands[-1], ancillas)
        else:
            new_operands = [qubit_map[x] for x in gate[1]]
            # [(new_qreg[qreg.index(qbit)] if isinstance(qbit, qreg.__class__) else qbit) for qbit in gate[1]]
            new_circ.append(gate[0], new_operands)

    new_circ = cczConvertor(new_circ) # new_circ.decompose()
    #print(new_circ)
    # Convert the circuit to QASM format and save it to a file
    qasm_str = new_circ.qasm()
    qasm_str = qasm_str.replace("ccx", "ccz")
    # Write the QASM string to a file
    with open(path + ".qasm", "w") as file:
        file.write(qasm_str)


def dotConvertor(circuit, filename, ancillas=None):
    # Convert the circuit to DAG
    if isinstance(circuit, QuantumCircuit):
        dag = circuit_to_dag(circuit)
    elif False and isinstance(circuit, cirq.Circuit):
        dag = _cirq_to_dag(circuit, ancillas)
    # print("CONVERT TO DOT")
    dot_str = dag_to_dot(dag)  # Convert the DAG to a DOT string
    with open(filename + ".dot", "w") as f:
        f.write(dot_str)
        

#def cirq_op_to_qiskit_instruction(op: cirq.Operation) -> Instruction:
#        """
#            This function converts a Cirq operation to a Qiskit Instruction.
#        """
#        print(op.gate, op.gate == cirq.CX, op.gate == cirq.CCX)
#        if op.gate == cirq.H:
#            return Instruction(name="H", num_qubits=1, num_clbits=0, params=[])
#        elif op.gate == cirq.X:
#            return Instruction(name="X", num_qubits=1, num_clbits=0, params=[])
#        elif op.gate == cirq.CX:
#            return Instruction(name="CX", num_qubits=2, num_clbits=0, params=[])
#        elif op.gate == cirq.CCX:
#            return Instruction(name="CCX", num_qubits=3, num_clbits=0, params=[])
#        elif op.gate == cirq.MeasurementGate:
#            return Instruction(name="measure", num_qubits=len(op.qubits), num_clbits=len(op.qubits), params=[])
#        else:
#            raise NotImplementedError(f"Conversion for {op.gate} not implemented.")



#def _cirq_to_dag(circuit: cirq.Circuit, ancillas: list) -> DAGCircuit:
#    # Initialize a Qiskit DAGCircuit object
#    dag = DAGCircuit()
#    print("ANCILLAS LIST ", ancillas)
#    # Create a QuantumRegister with the same number of qubits as in the Cirq circuit
#    # Fetch the addresses of GridQubits in the circuit
#    grid_qubits = circuit.all_qubits()  # This returns all qubits in the circuit
#    # Extract and sort addresses (row, col) for GridQubits
#    grid_qubits = [q for q in circuit.all_qubits() if isinstance(q, cirq.GridQubit)]
#    all_qubits = sorted(grid_qubits, key=lambda q: (q.row, q.col))
#    qubits = [x for i, x in enumerate(all_qubits) if i not in ancillas]
#    ancilla_list = [x for i, x in enumerate(all_qubits) if i in ancillas]
#    qubit_idx = [x for x in range(len(all_qubits)) if x not in ancillas]
#    qr = QuantumRegister(len(qubits), "q#")
#    ar = QuantumRegister(len(ancillas), "ancilla")
#    dag.add_qreg(qr)
#    dag.add_qreg(ar)
#    # Map Cirq qubits to Qiskit qubits (so we can reference them later)
#    qubit_mapping = {}  # q: Qubit(qr, idx) for idx, q in enumerate(qubits)}
#    for idx, q in enumerate(all_qubits):
#        if idx in qubit_idx:
#            qubit_mapping[q] = Qubit(qr, qubit_idx.index(idx))
#            print(q, qubits)
#        elif idx in ancillas:
#            qubit_mapping[q] = Qubit(ar, ancillas.index(idx))
#        else:
#            assert False
#    for moment_index, moment in enumerate(circuit):
#        for op in moment.operations:
#            # Get the Qiskit qubits corresponding to the qubits used by this operation
#            qiskit_qubits = [qubit_mapping[q] for q in op.qubits]            
#            # Convert Cirq operation to Qiskit Instruction
#            instruction = cirq_op_to_qiskit_instruction(op)
#            # Apply the operation to the DAG
#            dag.apply_operation_back(instruction, qiskit_qubits)
#    return dag

def dag_to_dot(dag):
    dot = pydot.Dot(graph_type='digraph')
        # Add source nodes for each qubit
    qubit_last_node = {}
    qubit_argument_map = {}
    all_anc = []
    edge_list = []
    total_qubits = 0
    for qubit in dag.qubits:
        qubit_label = str(total_qubits)
        qubit_name = f"q({total_qubits}) (d=2), op=in"
        qubit_argument_map[qubit] = qubit_label

        if "Ancilla" in str(qubit) or "ancilla" in str(qubit) or "anc" in str(qubit) or "carry" in str(qubit):
            dot.add_node(pydot.Node(qubit_label, label=qubit_name, qubits="\""+str(qubit_label)+"\"", matrix="\"None\"", ancilla=True))
            all_anc.append(int(qubit_label))
        else:
            dot.add_node(pydot.Node(qubit_label, label=qubit_name, qubits="\""+str(qubit_label)+"\"", matrix="\"None\"", ancilla=False))
        qubit_last_node[qubit] = qubit_label
        total_qubits += 1

    node_names = total_qubits
    # Add regular operation nodes and connect from the source nodes
    for node in dag.topological_op_nodes():
        node_name = str(node_names)
        target_qubit_names = [qubit_argument_map[x] for x in node.qargs]
        target_prefaced = [f"{t}" for t in target_qubit_names]
        #print(target_prefaced, ",".join(target_prefaced), type(",".join(target_prefaced)))

        if "MCXVChain" in str(node.op):
            no_anc = False
            remove_args = []
            #print(target_prefaced)
            target_prefaced = target_prefaced[:-1]
            #[int(x) for x in target_prefaced]
            #target_prefaced.sort()
            #target_prefaced = [str(x) for x in target_prefaced]
            #print(target_prefaced)
            #for q in target_prefaced:
            #    if int(q) in all_anc and not no_anc:
            #        no_anc = True
            #    elif int(q) in all_anc and no_anc:
            #        remove_args.append(q)
            #for q in remove_args:
            #    target_prefaced.remove(q)
            #print(remove_args)
            dot.add_node(pydot.Node(node_name, label="\"MCX\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[0,1],[1,0]])))
        elif "CX" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[0,1],[1,0]])))
        elif "XGate" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[0,1],[1,0]])))
        elif "X" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[0,1],[1,0]])))
        elif "HGate" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[math.sqrt(1/2),math.sqrt(1/2)],[math.sqrt(1/2),-1*math.sqrt(1/2)]])))
        elif "TdgGate" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[1,0],[0, cmath.exp(- cmath.pi * 1j/4 )]])))
        elif "TGate" in str(node.op):
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[1,0],[0, cmath.exp(cmath.pi * 1j/4 )]])))
        elif "barrier" in str(node.op):
            pass
        elif "RGate" in str(node.op):
            theta, phi = node.op.params  # Extract parameters
            matrix = [[cmath.cos(theta/2), -cmath.exp(1j * phi) * cmath.sin(theta/2)],
                      [cmath.exp(-1j * phi) * cmath.sin(theta/2), cmath.cos(theta/2)]]
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str(matrix)))
        elif "U3" in str(node.op) and [int(x/math.pi) for x in node.op.params] == [1, 0, 1]:
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str([[0,1],[1,0]])))
        elif "U3" in str(node.op) and node.op.params[1] == 0 and node.op.params[2] == 0:
            if node.op.params[0] != 0:
                print("found u3")
                thet = node.op.params[0]/2
                #print(thet)
                mat = np.array([[math.cos(thet), -1*math.sin(thet)], [math.sin(thet), math.cos(thet)]])
                #print(mat)
                #print(mat@ mat.T
                print(str(mat.tolist()))
                assert np.allclose(np.eye(2), mat @ mat.T)
                dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                    qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str(mat.tolist())))
        elif "U3" in str(node.op):
            # Extract parameters
            theta = node.op.params[0]
            phi = node.op.params[1]
            lambda_ = node.op.params[2]
            # Calculate the matrix for the U3 gate
            matrix = np.array([
                        [np.cos(theta / 2), -np.exp(1j * lambda_) * np.sin(theta / 2)],
                        [np.exp(1j * phi) * np.sin(theta / 2), np.exp(1j * (phi + lambda_)) * np.cos(theta / 2)]
                ])

            # Convert matrix to string representation
            matrix_str = str(matrix.tolist())
            # Create a dot file node
            target_prefaced = ["q0", "q1"]
            dot = pydot.Dot(graph_type="digraph")
            print(matrix_str, "\n" in matrix_str)
            dot.add_node(pydot.Node(node_name, label="\""+str(node.op)+"\"",
                       qubits="\"" + ",".join(target_prefaced)+"\"",
                       matrix=matrix_str.replace("\n", ",")))
        elif "U1" in str(node.op):
            # Matrix calculation for U1
            matrix = np.array([[1, 0], [0, np.exp(1j * node.op.params[0])]])
            # Dot node
            dot.add_node(pydot.Node(node_name, label="\"" + str(node.op)+ "\"", qubits="\"" + ",".join(target_prefaced)+"\"", matrix=str(matrix.tolist()).replace("\n", "")))
        elif "IGate" in str(node.op):
            pass
        else:
            print(node.op,  type(node.op), node, node.op.name, node.op.params, type(node.op.params), [int(x/math.pi) for x in node.op.params])
            print("\n\n\n\n\n")
            raise NotImplementedError
        for qubit in node.qargs:
            edge_list.append(pydot.Edge(qubit_last_node[qubit], node_name, label=f"{qubit_argument_map[qubit]}"))
            qubit_last_node[qubit] = node_name
        node_names += 1

    end_qubits = 0
    # Add sink nodes for each qubit and connect them from the last operation
    for qubit in dag.qubits:
        qubit_label = f"{end_qubits+node_names}"
        qubit_name = f"q({end_qubits}) (d=2), op=out"
        if "Ancilla" in str(qubit) or "ancilla" in str(qubit) or "ancc" in str(qubit) or "anc" in str(qubit) or "carry" in str(qubit):
            dot.add_node(pydot.Node(qubit_label, label=qubit_name, qubits=f"\"{qubit_argument_map[qubit]}\"", matrix="\"None\"", ancilla=True))
        else:
            dot.add_node(pydot.Node(qubit_label, label=qubit_name, qubits=f"\"{qubit_argument_map[qubit]}\"", matrix="\"None\"", ancilla=False))
        edge_list.append(pydot.Edge(qubit_last_node[qubit], qubit_label, label=f"{qubit_argument_map[qubit]}"))
        end_qubits += 1

    for edges in edge_list:
        dot.add_edge(edges)
    return dot.to_string()


# dag_drawer(dag, filename=filename+'.dot', style='plain')
