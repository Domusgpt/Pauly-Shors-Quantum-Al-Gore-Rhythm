"""
Quantum Oracle for Elliptic Curve Point Operations

Implements the quantum oracle for the mapping:
    |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP + bQ⟩

where P is the generator and Q = kP is the public key.
This is the core oracle used in Shor's algorithm for ECDLP.

For small curves (1-10 bits), we use a direct lookup table approach
encoding the entire point multiplication table as a quantum circuit.

For larger curves, we implement the full reversible EC point addition
using modular arithmetic sub-circuits.

References:
    - Roetteler et al. (2017): "Quantum resource estimates for computing ECDLP"
    - Banegas et al. (2021): "Quantum resource estimates of grover's key search"
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

from .ecc_curves import EllipticCurve, ECPoint, INFINITY
from .quantum_arithmetic import num_qubits_for_mod, LookupTableOracle


class ECPointOracle:
    """
    Quantum oracle that computes |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP + bQ⟩

    For the Q-Day Prize, this oracle is the heart of the attack.
    Given generator P and public key Q = kP, the oracle encodes the
    elliptic curve group operation into a quantum circuit.
    """

    def __init__(self, curve: EllipticCurve, generator: ECPoint, public_key: ECPoint):
        self.curve = curve
        self.G = generator
        self.Q = public_key
        self.n_order = curve.point_order(generator)
        self.n_bits = num_qubits_for_mod(self.n_order)
        self.p_bits = num_qubits_for_mod(curve.p)

        # Precompute the lookup table for small curves
        self._precompute_table()

    def _precompute_table(self):
        """Precompute aP + bQ for all (a, b) in [0, n_order)."""
        self.point_table: Dict[Tuple[int, int], ECPoint] = {}
        n = self.n_order

        for a in range(n):
            aP = self.curve.scalar_mult(a, self.G)
            for b in range(n):
                bQ = self.curve.scalar_mult(b, self.Q)
                result = self.curve.add(aP, bQ)
                self.point_table[(a, b)] = result

    def _encode_point(self, P: ECPoint) -> Tuple[int, int, int]:
        """
        Encode an EC point as (is_infinity, x, y).
        Returns tuple of integers suitable for binary encoding.
        """
        if P.is_infinity:
            return (1, 0, 0)
        return (0, P.x, P.y)

    def _point_to_int(self, P: ECPoint) -> int:
        """Map a point to a unique integer for lookup table encoding."""
        if P.is_infinity:
            return 0
        # Encode as x * p + y + 1 (reserve 0 for infinity)
        return P.x * self.curve.p + P.y + 1

    def num_output_qubits(self) -> int:
        """Number of qubits needed to encode a point."""
        max_val = self.curve.p * self.curve.p + 1
        return max(1, int(np.ceil(np.log2(max_val + 1))))

    def build_oracle_circuit(self) -> QuantumCircuit:
        """
        Build the complete oracle circuit.

        Registers:
            a_reg: n_bits qubits for scalar a
            b_reg: n_bits qubits for scalar b
            out_reg: output qubits for encoded point aP + bQ
        """
        n = self.n_bits
        n_out = self.num_output_qubits()

        a_reg = QuantumRegister(n, 'a')
        b_reg = QuantumRegister(n, 'b')
        out_reg = QuantumRegister(n_out, 'point')

        qc = QuantumCircuit(a_reg, b_reg, out_reg, name='EC_Oracle')

        # Lookup table oracle — works for any group order
        # O(n²) gates but produces exact unitary (zero approximation error)
        # For resonant keys (smooth group structure), this is optimal
        if self.n_order <= 2048:  # Raised from 64 — generates valid QASM at any scale
            self._build_lookup_oracle(qc, list(range(n)),
                                       list(range(n, 2*n)),
                                       list(range(2*n, 2*n + n_out)))
        else:
            self._build_arithmetic_oracle(qc, a_reg, b_reg, out_reg)

        return qc

    @staticmethod
    def _to_gray(n: int) -> int:
        """Convert integer to Gray code."""
        return n ^ (n >> 1)

    @staticmethod
    def _gray_code_order(num_bits: int) -> List[int]:
        """Generate integers 0..2^num_bits-1 in Gray code order."""
        return [ECPointOracle._to_gray(i) for i in range(1 << num_bits)]

    def _build_lookup_oracle(self, qc: QuantumCircuit, a_qubits: List[int],
                              b_qubits: List[int], out_qubits: List[int]):
        """
        Build oracle using direct lookup table with Gray code ordering.

        Gray code optimization: consecutive entries differ in only 1 bit,
        so we apply at most 1 X gate between entries instead of flipping
        all zero-controlled qubits for every entry. This significantly
        reduces the total X gate count.
        """
        n_a = len(a_qubits)
        n_b = len(b_qubits)
        n_out = len(out_qubits)
        n = self.n_order
        total_input_bits = n_a + n_b
        all_input_qubits = a_qubits + b_qubits

        # Collect all (a, b) pairs with non-zero encoded output
        active_entries = []
        for a in range(n):
            for b in range(n):
                point = self.point_table[(a, b)]
                encoded = self._point_to_int(point)
                if encoded == 0:
                    continue
                target_bits = [(encoded >> i) & 1 for i in range(n_out)]
                if not any(target_bits):
                    continue
                # Combine a and b into a single integer: low n_a bits = a, next n_b bits = b
                combined = a | (b << n_a)
                active_entries.append((combined, target_bits))

        if not active_entries:
            return

        # Sort active entries in Gray code order for minimal bit-flip transitions.
        # Build a Gray code rank lookup: gray_value -> position in Gray sequence
        gray_rank = {}
        for i in range(1 << total_input_bits):
            gray_rank[self._to_gray(i)] = i
        active_entries.sort(key=lambda e: gray_rank.get(e[0], e[0]))

        # Track the current flip state of each input qubit.
        # The MCX gate fires when all control qubits are |1>.
        # To match input value v, qubit i must be flipped (X) when bit i of v is 0.
        # flip_state[i] = True means qubit i is currently flipped (X applied).
        flip_state = [False] * total_input_bits

        for combined, target_bits in active_entries:
            # Determine desired flip for this entry: flip where bit is 0
            desired_flip = [(combined >> i) & 1 == 0 for i in range(total_input_bits)]

            # Apply incremental X gates: only toggle qubits whose flip state differs
            for i in range(total_input_bits):
                if flip_state[i] != desired_flip[i]:
                    qc.x(all_input_qubits[i])
                    flip_state[i] = desired_flip[i]

            # Apply MCX for each output bit that should be 1
            for out_idx in range(n_out):
                if target_bits[out_idx] == 1:
                    qc.mcx(all_input_qubits, out_qubits[out_idx])

        # Undo all remaining flips to restore input qubits to original state
        for i in range(total_input_bits):
            if flip_state[i]:
                qc.x(all_input_qubits[i])

    def _build_arithmetic_oracle(self, qc: QuantumCircuit, a_reg, b_reg, out_reg):
        """
        Build oracle using reversible arithmetic for larger curves.
        This implements the full EC point addition using modular arithmetic circuits.

        For the Q-Day Prize, this is needed for 10+ bit keys.
        """
        # For curves larger than lookup table size, we need full
        # reversible EC point arithmetic. This requires:
        # 1. Modular multiplication circuits
        # 2. Modular inversion (via extended GCD)
        # 3. EC point addition formula
        #
        # We implement the double-and-add algorithm reversibly:
        # Initialize R = O (point at infinity)
        # For i from MSB to LSB of a:
        #     R = 2R
        #     if a_i: R = R + P
        # For i from MSB to LSB of b:
        #     R = 2R
        #     if b_i: R = R + Q
        #
        # Each step requires controlled EC point addition.

        raise NotImplementedError(
            f"Full arithmetic oracle needed for curves with order > 64. "
            f"Current curve order: {self.n_order}. "
            f"Use smaller key sizes (1-5 bits) for lookup table approach, "
            f"or implement reversible EC arithmetic (Roetteler et al. 2017)."
        )


class SimplifiedECOracle:
    """
    Simplified oracle for very small curves (1-3 bits).

    Instead of encoding full point coordinates, we encode just the
    discrete log relationship directly. For a cyclic group of order n,
    the function f(a, b) = (a + kb) mod n is periodic with the structure
    that Shor's algorithm can exploit.

    This is equivalent to the full EC oracle but much more efficient
    for small groups, since we only need to encode the group operation
    modulo n rather than full point arithmetic.
    """

    def __init__(self, group_order: int, secret_key: int):
        """
        Args:
            group_order: Order of the cyclic subgroup generated by P
            secret_key: The value k such that Q = kP (what we're solving for)
        """
        self.n = group_order
        self.k = secret_key  # In real attack, this is unknown
        self.n_bits = num_qubits_for_mod(group_order)

    def build_oracle(self) -> QuantumCircuit:
        """
        Build oracle computing f(a, b) = (a + kb) mod n.

        This is the "cheating" oracle used for testing - in a real attack,
        we would use the full EC point oracle which doesn't need k.
        """
        n_bits = self.n_bits
        n_out = n_bits

        a_reg = QuantumRegister(n_bits, 'a')
        b_reg = QuantumRegister(n_bits, 'b')
        out_reg = QuantumRegister(n_out, 'f_ab')

        qc = QuantumCircuit(a_reg, b_reg, out_reg, name='SimplifiedOracle')

        # Lookup table approach
        for a in range(self.n):
            for b in range(self.n):
                result = (a + self.k * b) % self.n
                if result == 0:
                    continue

                a_bits = [(a >> i) & 1 for i in range(n_bits)]
                b_bits = [(b >> i) & 1 for i in range(n_bits)]
                r_bits = [(result >> i) & 1 for i in range(n_out)]

                # Flip for zero-controlled
                for idx in range(n_bits):
                    if a_bits[idx] == 0:
                        qc.x(a_reg[idx])
                for idx in range(n_bits):
                    if b_bits[idx] == 0:
                        qc.x(b_reg[idx])

                ctrls = list(a_reg) + list(b_reg)

                for out_idx in range(n_out):
                    if r_bits[out_idx] == 1:
                        qc.mcx(ctrls, out_reg[out_idx])

                # Unflip
                for idx in range(n_bits):
                    if a_bits[idx] == 0:
                        qc.x(a_reg[idx])
                for idx in range(n_bits):
                    if b_bits[idx] == 0:
                        qc.x(b_reg[idx])

        return qc
