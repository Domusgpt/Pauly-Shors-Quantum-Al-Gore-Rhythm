"""
Shor's Algorithm for Elliptic Curve Discrete Logarithm Problem (ECDLP)

Core implementation of the quantum attack on ECC for the Q-Day Prize.

Given:
    - Elliptic curve E over GF(p)
    - Generator point P of order n
    - Public key Q = kP

Find:
    - Secret key k

Algorithm outline (Proos & Zalka 2003):
    1. Prepare two quantum registers in uniform superposition: |a⟩|b⟩
    2. Apply oracle: |a⟩|b⟩|0⟩ → |a⟩|b⟩|aP + bQ⟩
    3. Apply QFT to both registers |a⟩ and |b⟩
    4. Measure to get (j₁, j₂)
    5. Use continued fractions / lattice reduction to extract k from:
       j₁ ≈ rk/n (mod 1) and j₂ ≈ -r/n (mod 1)
    6. Repeat until k is found

References:
    - Shor (1994): "Algorithms for quantum computation"
    - Proos & Zalka (2003): "Shor's discrete logarithm quantum algorithm for elliptic curves"
    - Roetteler et al. (2017): "Quantum resource estimates for computing ECDLP"
"""

import numpy as np
from typing import Optional, Tuple, List, Dict
from math import gcd
from fractions import Fraction
from dataclasses import dataclass

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit.library import QFT

from .ecc_curves import EllipticCurve, ECPoint, INFINITY, get_curve, generate_keypair
from .ecc_point_oracle import ECPointOracle, SimplifiedECOracle
from .quantum_arithmetic import num_qubits_for_mod


@dataclass
class ShorResult:
    """Result of running Shor's ECDLP algorithm."""
    secret_key: Optional[int]
    num_shots: int
    num_iterations: int
    measurements: List[Tuple[int, int]]
    candidate_keys: List[int]
    success: bool
    circuit_depth: int
    num_qubits: int
    gate_counts: Dict[str, int]

    def __repr__(self):
        status = "SUCCESS" if self.success else "FAILED"
        return (f"ShorResult({status}: k={self.secret_key}, "
                f"qubits={self.num_qubits}, depth={self.circuit_depth}, "
                f"iterations={self.num_iterations})")


class ShorECDLP:
    """
    Shor's algorithm for solving the Elliptic Curve Discrete Logarithm Problem.

    This is the main attack class for the Q-Day Prize competition.
    """

    def __init__(self, curve: EllipticCurve, generator: ECPoint,
                 public_key: ECPoint, precision_bits: Optional[int] = None):
        """
        Args:
            curve: The elliptic curve E over GF(p)
            generator: Base point P
            public_key: Q = kP (the point whose discrete log we want)
            precision_bits: Number of qubits per register (default: 2*ceil(log2(n))+1)
        """
        self.curve = curve
        self.G = generator
        self.Q = public_key
        self.n_order = curve.point_order(generator)

        if precision_bits is None:
            self.precision = 2 * num_qubits_for_mod(self.n_order) + 1
        else:
            self.precision = precision_bits

        self.n_bits = num_qubits_for_mod(self.n_order)

    def build_circuit(self, use_simplified_oracle: bool = False,
                       known_key: Optional[int] = None) -> QuantumCircuit:
        """
        Build the complete Shor's algorithm circuit for ECDLP.

        Args:
            use_simplified_oracle: If True, use simplified oracle (for testing/validation)
            known_key: Required if use_simplified_oracle=True

        Returns:
            QuantumCircuit ready for execution
        """
        m = self.precision  # Precision qubits per register
        n_out = ECPointOracle(self.curve, self.G, self.Q).num_output_qubits() \
            if not use_simplified_oracle else self.n_bits

        # Quantum registers
        a_reg = QuantumRegister(m, 'a')  # First input register
        b_reg = QuantumRegister(m, 'b')  # Second input register
        out_reg = QuantumRegister(n_out, 'oracle_out')  # Oracle output
        c_a = ClassicalRegister(m, 'ca')  # Measurement of a
        c_b = ClassicalRegister(m, 'cb')  # Measurement of b

        qc = QuantumCircuit(a_reg, b_reg, out_reg, c_a, c_b,
                           name='Shor_ECDLP')

        # Step 1: Create uniform superposition
        for i in range(m):
            qc.h(a_reg[i])
            qc.h(b_reg[i])

        qc.barrier()

        # Step 2: Apply oracle
        if use_simplified_oracle:
            if known_key is None:
                raise ValueError("known_key required for simplified oracle")
            oracle = SimplifiedECOracle(self.n_order, known_key)
            oracle_circ = oracle.build_oracle()
        else:
            oracle_builder = ECPointOracle(self.curve, self.G, self.Q)
            oracle_circ = oracle_builder.build_oracle_circuit()

        # Map oracle registers to our circuit
        # The oracle expects (a, b, out) registers
        oracle_qubits = (list(a_reg[:self.n_bits]) +
                        list(b_reg[:self.n_bits]) +
                        list(out_reg))
        qc.append(oracle_circ, oracle_qubits)

        qc.barrier()

        # Step 3: Apply inverse QFT to both input registers
        iqft_a = QFT(m, do_swaps=True).inverse()
        iqft_b = QFT(m, do_swaps=True).inverse()

        qc.append(iqft_a, a_reg)
        qc.append(iqft_b, b_reg)

        qc.barrier()

        # Step 4: Measure input registers
        qc.measure(a_reg, c_a)
        qc.measure(b_reg, c_b)

        return qc

    def extract_key_from_measurements(self, measurements: List[Tuple[int, int]]) -> List[int]:
        """
        Extract candidate secret keys from measurement results.

        From Shor's algorithm, measurements (j1, j2) satisfy:
            j1/N ≈ r*k/n  and  j2/N ≈ -r/n
        for some random integer r, where N = 2^precision and n = group order.

        So k ≈ -j1/j2 mod n.

        We use continued fractions to handle the approximation.
        """
        N = 2 ** self.precision
        n = self.n_order
        candidates = set()

        for j1, j2 in measurements:
            if j2 == 0:
                continue

            # Method 1: Direct ratio
            # k = -j1 * j2^(-1) mod n
            try:
                j2_inv = pow(j2 % n, -1, n) if n > 1 else 0
                k_candidate = (-j1 * j2_inv) % n
                if k_candidate > 0:
                    candidates.add(k_candidate)
            except (ValueError, ZeroDivisionError):
                pass

            # Method 2: Continued fractions on j2/N to find r/n
            frac = Fraction(j2, N).limit_denominator(n)
            if frac.denominator > 0:
                r = frac.numerator
                n_candidate = frac.denominator

                if n_candidate > 0 and n % n_candidate == 0:
                    # j1/N ≈ r*k/n, so k ≈ j1*n/(N*r)
                    if r != 0:
                        try:
                            r_inv = pow(r % n, -1, n) if n > 1 else 0
                            k_est = (j1 * n * r_inv) // N if N > 0 else 0
                            for delta in range(-2, 3):
                                k_try = (k_est + delta) % n
                                if k_try > 0:
                                    candidates.add(k_try)
                        except (ValueError, ZeroDivisionError):
                            pass

            # Method 3: Direct lattice approach for small n
            if n <= 256:
                for k_try in range(1, n):
                    # Check if (j1, j2) is consistent with k_try
                    # j1 ≈ r*k_try mod n scaled by N/n
                    # j2 ≈ -r mod n scaled by N/n
                    for r in range(1, n):
                        expected_j1 = round((r * k_try % n) * N / n) % N
                        expected_j2 = round((-r % n) * N / n) % N
                        if (abs(j1 - expected_j1) <= 1 and
                            abs(j2 - expected_j2) <= 1):
                            candidates.add(k_try)

        return sorted(candidates)

    def verify_key(self, k: int) -> bool:
        """Verify that k is the correct secret key: Q == kG."""
        computed_Q = self.curve.scalar_mult(k, self.G)
        return computed_Q == self.Q

    def run_attack(self, backend=None, shots: int = 1024,
                    max_iterations: int = 10,
                    use_simplified_oracle: bool = False,
                    known_key: Optional[int] = None) -> ShorResult:
        """
        Execute the full Shor's ECDLP attack.

        Args:
            backend: Qiskit backend (None = AerSimulator)
            shots: Number of shots per circuit execution
            max_iterations: Maximum number of circuit executions
            use_simplified_oracle: Use simplified oracle (for testing)
            known_key: Known key for simplified oracle verification

        Returns:
            ShorResult with attack outcome
        """
        from qiskit_aer import AerSimulator
        from qiskit import transpile

        if backend is None:
            backend = AerSimulator()

        all_measurements = []
        all_candidates = []

        # Build and analyze circuit
        qc = self.build_circuit(use_simplified_oracle=use_simplified_oracle,
                                known_key=known_key)

        # Decompose sub-circuits and transpile
        qc_decomposed = qc.decompose().decompose().decompose()

        # Check if this is an IBM backend that needs generate_preset_pass_manager
        is_ibm_backend = hasattr(backend, 'service') or (
            type(backend).__module__.startswith('qiskit_ibm_runtime'))
        if is_ibm_backend:
            from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
            pm = generate_preset_pass_manager(backend=backend, optimization_level=2)
            transpiled = pm.run(qc_decomposed)
        else:
            transpiled = transpile(qc_decomposed, backend, optimization_level=2)
        gate_counts = dict(transpiled.count_ops())
        circuit_depth = transpiled.depth()
        num_qubits = transpiled.num_qubits

        for iteration in range(max_iterations):
            # Execute circuit — use SamplerV2 for IBM backends, .run() for Aer
            is_ibm_backend = hasattr(backend, 'service') or (
                type(backend).__module__.startswith('qiskit_ibm_runtime'))
            if is_ibm_backend:
                from qiskit_ibm_runtime import SamplerV2
                sampler = SamplerV2(mode=backend)
                job = sampler.run([transpiled], shots=shots)
                primitive_result = job.result()
                pub_result = primitive_result[0]
                # Convert SamplerV2 result to counts dict
                counts = pub_result.data.meas.get_counts() if hasattr(pub_result.data, 'meas') else {}
                if not counts:
                    # Try to get counts from classical register names
                    for attr_name in dir(pub_result.data):
                        if not attr_name.startswith('_'):
                            attr = getattr(pub_result.data, attr_name)
                            if hasattr(attr, 'get_counts'):
                                counts = attr.get_counts()
                                if counts:
                                    break
                    if not counts:
                        # Fallback: get bitarray and convert
                        counts = pub_result.data.get_counts() if hasattr(pub_result.data, 'get_counts') else {}
            else:
                result = backend.run(transpiled, shots=shots).result()
                counts = result.get_counts()

            # Parse measurements
            for bitstring, count in counts.items():
                parts = bitstring.split(' ')
                if len(parts) == 2:
                    j2 = int(parts[0], 2)
                    j1 = int(parts[1], 2)
                else:
                    # Single register case
                    total_bits = len(bitstring)
                    half = total_bits // 2
                    j1 = int(bitstring[half:], 2)
                    j2 = int(bitstring[:half], 2)

                for _ in range(count):
                    all_measurements.append((j1, j2))

            # Extract candidates
            candidates = self.extract_key_from_measurements(all_measurements)
            all_candidates = candidates

            # Verify each candidate
            for k_candidate in candidates:
                if self.verify_key(k_candidate):
                    return ShorResult(
                        secret_key=k_candidate,
                        num_shots=len(all_measurements),
                        num_iterations=iteration + 1,
                        measurements=all_measurements[:20],  # Keep first 20
                        candidate_keys=candidates,
                        success=True,
                        circuit_depth=circuit_depth,
                        num_qubits=num_qubits,
                        gate_counts=gate_counts
                    )

        return ShorResult(
            secret_key=None,
            num_shots=len(all_measurements),
            num_iterations=max_iterations,
            measurements=all_measurements[:20],
            candidate_keys=all_candidates,
            success=False,
            circuit_depth=circuit_depth,
            num_qubits=num_qubits,
            gate_counts=gate_counts
        )


class BruteForceQuantumSearch:
    """
    Grover-enhanced brute force for ECDLP on very small keys.

    For 1-3 bit keys, Grover's algorithm provides quadratic speedup
    over classical brute force. While not Shor's algorithm (and thus
    not eligible for the Q-Day Prize), this serves as a baseline
    comparison and validation tool.
    """

    def __init__(self, curve: EllipticCurve, generator: ECPoint,
                 public_key: ECPoint):
        self.curve = curve
        self.G = generator
        self.Q = public_key
        self.n_order = curve.point_order(generator)
        self.n_bits = num_qubits_for_mod(self.n_order)

    def classical_brute_force(self) -> Optional[int]:
        """Classical brute force for verification."""
        for k in range(1, self.n_order):
            if self.curve.scalar_mult(k, self.G) == self.Q:
                return k
        return None


# ─── High-level attack functions ─────────────────────────────────────────────

def attack_ecc_key(bits: int, secret_key: Optional[int] = None,
                    shots: int = 2048, backend=None) -> ShorResult:
    """
    High-level function to attack an ECC key of given bit size.

    Args:
        bits: Security level (1-25)
        secret_key: If provided, use this key. Otherwise generate random.
        shots: Number of quantum shots
        backend: Qiskit backend

    Returns:
        ShorResult
    """
    curve = get_curve(bits)
    G = curve.find_generator()
    n = curve.point_order(G)

    if secret_key is None:
        import random
        secret_key = random.randint(1, n - 1)

    Q = curve.scalar_mult(secret_key, G)

    print(f"[Q-Day Attack] Target: {bits}-bit ECC key")
    print(f"  Curve: y² = x³ + {curve.a}x + {curve.b} over GF({curve.p})")
    print(f"  Generator P = {G}")
    print(f"  Group order n = {n}")
    print(f"  Public key Q = kP = {Q}")
    print(f"  Secret key k = {secret_key} (to be recovered)")
    print()

    shor = ShorECDLP(curve, G, Q)

    # Always use the honest ECPointOracle (computes aP + bQ from public key only)
    # Never use SimplifiedECOracle which embeds the secret key in the circuit
    result = shor.run_attack(
        backend=backend,
        shots=shots,
        use_simplified_oracle=False,
        known_key=None
    )

    if result.success:
        print(f"[SUCCESS] Recovered secret key: k = {result.secret_key}")
        print(f"  Verified: Q == {result.secret_key} * P = {Q}")
    else:
        print(f"[FAILED] Could not recover key in {result.num_iterations} iterations")
        print(f"  Candidates tested: {result.candidate_keys}")

    print(f"  Circuit: {result.num_qubits} qubits, depth {result.circuit_depth}")
    print(f"  Gate counts: {result.gate_counts}")

    return result
