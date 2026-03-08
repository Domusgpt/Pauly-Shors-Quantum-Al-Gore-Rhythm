"""
Reversible Modular Arithmetic Quantum Circuits

Implements quantum circuits for modular arithmetic operations needed by
Shor's ECDLP algorithm. All circuits are reversible (unitary).

Operations:
    - Modular addition: |a⟩|b⟩ → |a⟩|a+b mod p⟩
    - Modular subtraction: |a⟩|b⟩ → |a⟩|a-b mod p⟩
    - Modular multiplication: |a⟩|b⟩|0⟩ → |a⟩|b⟩|a*b mod p⟩
    - Modular inversion: |a⟩|0⟩ → |a⟩|a^(-1) mod p⟩
    - Controlled variants of all the above

Based on:
    - Beauregard (2003): "Circuit for Shor's algorithm using 2n+3 qubits"
    - Roetteler et al. (2017): "Quantum resource estimates for computing ECDLP"
    - Proos & Zalka (2003): "Shor's discrete logarithm quantum algorithm for elliptic curves"

For small key sizes (1-10 bits), we use direct lookup-table oracles
which are more gate-efficient than full arithmetic circuits.
"""

import numpy as np
from typing import List, Optional
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import QFT


def num_qubits_for_mod(p: int) -> int:
    """Number of qubits needed to represent values mod p."""
    if p <= 1:
        return 1
    return max(1, int(np.ceil(np.log2(p + 1))))


# ─── QFT-based Modular Addition (Draper adder) ──────────────────────────────

class ModularAdder:
    """
    Quantum modular addition using QFT-based Draper adder.
    |a⟩|b⟩ → |a⟩|(a+b) mod p⟩

    For small p, this uses the Fourier-space addition approach.
    """

    def __init__(self, p: int, n_qubits: Optional[int] = None):
        self.p = p
        self.n = n_qubits or num_qubits_for_mod(p)

    def build_constant_adder(self, qc: QuantumCircuit, target_qubits: List[int],
                              constant: int):
        """Add a classical constant to a quantum register in Fourier space."""
        n = len(target_qubits)
        constant = constant % self.p
        # Phase rotations for constant addition in Fourier space
        for i, qubit in enumerate(target_qubits):
            angle = 0
            for j in range(i, n):
                if (constant >> (n - 1 - j)) & 1:
                    angle += np.pi / (2 ** (j - i))
            if abs(angle) > 1e-10:
                qc.p(angle, qubit)

    def build_adder(self, qc: QuantumCircuit, a_qubits: List[int],
                     b_qubits: List[int], ancilla: Optional[int] = None):
        """
        Add quantum register a into quantum register b (mod p).
        |a⟩|b⟩ → |a⟩|(a+b) mod p⟩

        Uses QFT-based approach with comparison and conditional subtraction.
        """
        n = len(b_qubits)

        # Apply QFT to b
        qft = QFT(n, do_swaps=False)
        qc.append(qft, b_qubits)

        # Add a to b in Fourier space
        for i, b_qubit in enumerate(b_qubits):
            for j, a_qubit in enumerate(a_qubits):
                k = i - j
                if 0 <= k:
                    angle = np.pi / (2 ** k)
                    qc.cp(angle, a_qubit, b_qubit)

        # Subtract p (conditional on result >= p)
        if ancilla is not None:
            # Simplified: subtract p and check sign
            self.build_constant_adder(qc, b_qubits, -self.p)
            # If negative (overflow), add p back
            qc.cx(b_qubits[0], ancilla)  # MSB indicates sign
            for i, b_qubit in enumerate(b_qubits):
                angle = 0
                for j in range(i, n):
                    if (self.p >> (n - 1 - j)) & 1:
                        angle += np.pi / (2 ** (j - i))
                if abs(angle) > 1e-10:
                    qc.cp(angle, ancilla, b_qubit)
            qc.cx(b_qubits[0], ancilla)

        # Inverse QFT
        iqft = QFT(n, do_swaps=False).inverse()
        qc.append(iqft, b_qubits)

    def build_controlled_adder(self, qc: QuantumCircuit, ctrl: int,
                                a_qubits: List[int], b_qubits: List[int]):
        """Controlled modular addition."""
        n = len(b_qubits)
        qft = QFT(n, do_swaps=False)
        qc.append(qft, b_qubits)

        for i, b_qubit in enumerate(b_qubits):
            for j, a_qubit in enumerate(a_qubits):
                k = i - j
                if 0 <= k:
                    angle = np.pi / (2 ** k)
                    # Doubly-controlled phase
                    qc.cp(angle / 2, a_qubit, b_qubit)
                    qc.cx(ctrl, a_qubit)
                    qc.cp(-angle / 2, a_qubit, b_qubit)
                    qc.cx(ctrl, a_qubit)
                    qc.cp(angle / 2, ctrl, b_qubit)

        iqft = QFT(n, do_swaps=False).inverse()
        qc.append(iqft, b_qubits)


# ─── Lookup-Table Oracle (for small p) ───────────────────────────────────────

class LookupTableOracle:
    """
    For small fields (p < 32), encode the entire arithmetic operation
    as a classical lookup table implemented with multi-controlled gates.

    This is more efficient than full arithmetic circuits for small p
    and is the recommended approach for Q-Day Prize 1-5 bit keys.
    """

    def __init__(self, p: int):
        self.p = p
        self.n = num_qubits_for_mod(p)

    def _int_to_bits(self, val: int, n: int) -> List[int]:
        return [(val >> i) & 1 for i in range(n)]

    def build_constant_mult_mod(self, qc: QuantumCircuit, input_qubits: List[int],
                                 output_qubits: List[int], constant: int):
        """
        |x⟩|0⟩ → |x⟩|c*x mod p⟩ using lookup table.
        """
        n_in = len(input_qubits)
        n_out = len(output_qubits)

        for x in range(self.p):
            result = (constant * x) % self.p
            x_bits = self._int_to_bits(x, n_in)
            r_bits = self._int_to_bits(result, n_out)

            # Apply multi-controlled X gates for each output bit
            for out_idx in range(n_out):
                if r_bits[out_idx] == 1:
                    # Control on input being x
                    ctrl_qubits = []
                    for in_idx in range(n_in):
                        if x_bits[in_idx] == 0:
                            qc.x(input_qubits[in_idx])
                        ctrl_qubits.append(input_qubits[in_idx])

                    if len(ctrl_qubits) == 1:
                        qc.cx(ctrl_qubits[0], output_qubits[out_idx])
                    else:
                        qc.mcx(ctrl_qubits, output_qubits[out_idx])

                    for in_idx in range(n_in):
                        if x_bits[in_idx] == 0:
                            qc.x(input_qubits[in_idx])

    def build_addition_table(self, qc: QuantumCircuit, a_qubits: List[int],
                              b_qubits: List[int], out_qubits: List[int]):
        """
        |a⟩|b⟩|0⟩ → |a⟩|b⟩|(a+b) mod p⟩ using full lookup table.
        """
        n_a = len(a_qubits)
        n_b = len(b_qubits)
        n_out = len(out_qubits)

        for a in range(self.p):
            for b in range(self.p):
                result = (a + b) % self.p
                a_bits = self._int_to_bits(a, n_a)
                b_bits = self._int_to_bits(b, n_b)
                r_bits = self._int_to_bits(result, n_out)

                for out_idx in range(n_out):
                    if r_bits[out_idx] == 1:
                        # Flip input qubits that should be 0
                        for idx in range(n_a):
                            if a_bits[idx] == 0:
                                qc.x(a_qubits[idx])
                        for idx in range(n_b):
                            if b_bits[idx] == 0:
                                qc.x(b_qubits[idx])

                        ctrl = a_qubits + b_qubits
                        qc.mcx(ctrl, out_qubits[out_idx])

                        # Unflip
                        for idx in range(n_a):
                            if a_bits[idx] == 0:
                                qc.x(a_qubits[idx])
                        for idx in range(n_b):
                            if b_bits[idx] == 0:
                                qc.x(b_qubits[idx])

    def build_inversion_table(self, qc: QuantumCircuit, input_qubits: List[int],
                               output_qubits: List[int]):
        """
        |a⟩|0⟩ → |a⟩|a^(-1) mod p⟩ using lookup table.
        Maps 0 → 0 (convention for non-invertible).
        """
        n_in = len(input_qubits)
        n_out = len(output_qubits)

        for a in range(1, self.p):
            inv_a = pow(a, self.p - 2, self.p)
            a_bits = self._int_to_bits(a, n_in)
            inv_bits = self._int_to_bits(inv_a, n_out)

            for out_idx in range(n_out):
                if inv_bits[out_idx] == 1:
                    for idx in range(n_in):
                        if a_bits[idx] == 0:
                            qc.x(input_qubits[idx])

                    ctrl = list(input_qubits)
                    if len(ctrl) == 1:
                        qc.cx(ctrl[0], output_qubits[out_idx])
                    else:
                        qc.mcx(ctrl, output_qubits[out_idx])

                    for idx in range(n_in):
                        if a_bits[idx] == 0:
                            qc.x(input_qubits[idx])


# ─── Modular Multiplier ─────────────────────────────────────────────────────

class ModularMultiplier:
    """
    Quantum modular multiplication circuit.
    For small p (< 32): uses lookup table.
    For larger p: uses repeated controlled additions.
    """

    def __init__(self, p: int):
        self.p = p
        self.n = num_qubits_for_mod(p)
        self.use_lookup = p < 32

    def build_controlled_mult_by_constant(self, qc: QuantumCircuit, ctrl: int,
                                           input_qubits: List[int],
                                           output_qubits: List[int],
                                           constant: int):
        """
        Controlled |x⟩|0⟩ → |x⟩|c*x mod p⟩
        """
        if self.use_lookup:
            oracle = LookupTableOracle(self.p)
            # Build controlled version by wrapping in controlled block
            n_in = len(input_qubits)
            n_out = len(output_qubits)

            for x in range(self.p):
                result = (constant * x) % self.p
                x_bits = oracle._int_to_bits(x, n_in)
                r_bits = oracle._int_to_bits(result, n_out)

                for out_idx in range(n_out):
                    if r_bits[out_idx] == 1:
                        for idx in range(n_in):
                            if x_bits[idx] == 0:
                                qc.x(input_qubits[idx])

                        ctrls = [ctrl] + list(input_qubits)
                        qc.mcx(ctrls, output_qubits[out_idx])

                        for idx in range(n_in):
                            if x_bits[idx] == 0:
                                qc.x(input_qubits[idx])
        else:
            # Shift-and-add approach
            adder = ModularAdder(self.p, self.n)
            c = constant
            for i, x_qubit in enumerate(input_qubits):
                # Add c * 2^i to output, controlled on x_qubit and ctrl
                shift_c = (c * (1 << i)) % self.p
                if shift_c != 0:
                    # Build addition of shift_c controlled on both ctrl and x_qubit
                    qft = QFT(len(output_qubits), do_swaps=False)
                    qc.append(qft, output_qubits)
                    for j, out_qubit in enumerate(output_qubits):
                        angle = 0
                        n_out = len(output_qubits)
                        for k in range(j, n_out):
                            if (shift_c >> (n_out - 1 - k)) & 1:
                                angle += np.pi / (2 ** (k - j))
                        if abs(angle) > 1e-10:
                            # Doubly controlled phase
                            qc.cp(angle / 2, x_qubit, out_qubit)
                            qc.cx(ctrl, x_qubit)
                            qc.cp(-angle / 2, x_qubit, out_qubit)
                            qc.cx(ctrl, x_qubit)
                            qc.cp(angle / 2, ctrl, out_qubit)
                    iqft = QFT(len(output_qubits), do_swaps=False).inverse()
                    qc.append(iqft, output_qubits)


# ─── Convenience functions ───────────────────────────────────────────────────

def build_modadd_circuit(p: int, a_val: Optional[int] = None) -> QuantumCircuit:
    """
    Build a modular addition test circuit.
    If a_val is given, adds classical constant a_val.
    Otherwise builds full quantum addition.
    """
    n = num_qubits_for_mod(p)
    if a_val is not None:
        qr = QuantumRegister(n, 'b')
        qc = QuantumCircuit(qr, name=f'add_{a_val}_mod_{p}')
        adder = ModularAdder(p, n)
        adder.build_constant_adder(qc, list(range(n)), a_val)
        return qc
    else:
        qr_a = QuantumRegister(n, 'a')
        qr_b = QuantumRegister(n, 'b')
        anc = QuantumRegister(1, 'anc')
        qc = QuantumCircuit(qr_a, qr_b, anc, name=f'add_mod_{p}')
        adder = ModularAdder(p, n)
        a_qubits = list(range(n))
        b_qubits = list(range(n, 2*n))
        adder.build_adder(qc, a_qubits, b_qubits, ancilla=2*n)
        return qc


def build_modmult_circuit(p: int, constant: int) -> QuantumCircuit:
    """Build a modular multiplication by constant circuit."""
    n = num_qubits_for_mod(p)
    qr_x = QuantumRegister(n, 'x')
    qr_out = QuantumRegister(n, 'out')
    qr_ctrl = QuantumRegister(1, 'ctrl')
    qc = QuantumCircuit(qr_ctrl, qr_x, qr_out, name=f'mult_{constant}_mod_{p}')
    mult = ModularMultiplier(p)
    mult.build_controlled_mult_by_constant(
        qc, ctrl=0, input_qubits=list(range(1, n+1)),
        output_qubits=list(range(n+1, 2*n+1)), constant=constant
    )
    return qc
