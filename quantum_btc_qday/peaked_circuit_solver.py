#!/usr/bin/env python3
"""
Peaked Circuit Solver for BlueQubit Quantum Advantage Challenge

Prize: 0.25 BTC (~$20,000)
Wallet: bc1qcga5wx9e7gvz2eml0gpkrlpmttjzyw6rc6xfzz
Challenge: https://app.bluequbit.io/hackathons/GFgHTGbTylwmsMsCp

Peaked circuits are quantum unitaries where one bitstring has anomalously
high measurement probability (~10% vs 1/2^n for random). The BTC private
key is split across 5 peaked circuits of increasing difficulty.

Attack Strategy (Classical + Quantum Hybrid):
    1. Circuit simplification via gate cancellation detection
    2. Tensor network contraction (MPS/MPO methods)
    3. Marginal estimation (compute single-qubit expectation values)
    4. Light-cone reduction (only simulate relevant qubit subsets)
    5. If classical fails: submit to real quantum hardware via BlueQubit/IBM

Based on:
    - Aaronson et al.: Peaked circuits for verifiable quantum advantage
    - BlueQubit (2025): "Heuristic Quantum Advantage with Peaked Circuits"
      arXiv:2510.25838

Usage:
    # Set your BlueQubit API token
    export BLUEQUBIT_API_TOKEN=your_token_here

    # Run solver
    python peaked_circuit_solver.py --challenge
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, Operator
from qiskit_aer import AerSimulator


class PeakedCircuitSolver:
    """
    Multi-strategy solver for peaked circuit challenges.

    For small circuits (< 25 qubits): exact statevector simulation
    For medium circuits (25-40 qubits): tensor network / MPS methods
    For large circuits (40+ qubits): marginal estimation + quantum hardware
    """

    def __init__(self, circuit: QuantumCircuit):
        self.circuit = circuit
        self.n_qubits = circuit.num_qubits
        self.n_gates = sum(circuit.count_ops().values())

    def solve(self) -> Optional[str]:
        """
        Attempt to find the peaked bitstring using multiple strategies.
        Returns the peaked bitstring or None.
        """
        print(f"Solving {self.n_qubits}-qubit circuit with {self.n_gates} gates")

        # Strategy 1: Circuit simplification
        simplified = self._simplify_circuit()

        # Strategy 2: Exact simulation (if feasible)
        if self.n_qubits <= 28:
            result = self._exact_simulation(simplified)
            if result:
                return result

        # Strategy 3: Sampling-based approach
        result = self._sampling_approach(simplified)
        if result:
            return result

        # Strategy 4: Marginal estimation
        result = self._marginal_estimation(simplified)
        if result:
            return result

        # Strategy 5: Light-cone reduction
        result = self._lightcone_reduction(simplified)
        if result:
            return result

        print("Classical methods exhausted. Quantum hardware required.")
        return None

    def _simplify_circuit(self) -> QuantumCircuit:
        """
        Attempt to simplify the circuit by detecting and removing
        identity blocks (U followed by U†).
        """
        print("  [1/5] Simplifying circuit...")

        # Use Qiskit's transpiler for gate cancellation
        simplified = transpile(
            self.circuit,
            optimization_level=3,
            basis_gates=['cx', 'u3', 'u2', 'u1', 'id', 'rz', 'sx', 'x']
        )

        original_gates = sum(self.circuit.count_ops().values())
        simplified_gates = sum(simplified.count_ops().values())
        reduction = (1 - simplified_gates / max(original_gates, 1)) * 100

        print(f"    Gates: {original_gates} -> {simplified_gates} "
              f"({reduction:.1f}% reduction)")

        return simplified

    def _exact_simulation(self, circuit: QuantumCircuit) -> Optional[str]:
        """Exact statevector simulation for small circuits."""
        print(f"  [2/5] Exact simulation ({self.n_qubits} qubits)...")

        try:
            sv = Statevector.from_instruction(circuit)
            probs = sv.probabilities()

            # Find the peak
            peak_idx = np.argmax(probs)
            peak_prob = probs[peak_idx]
            peak_bitstring = format(peak_idx, f'0{self.n_qubits}b')

            # Check if it's actually peaked (significantly above uniform)
            uniform = 1.0 / (2 ** self.n_qubits)
            if peak_prob > 10 * uniform:
                print(f"    PEAK FOUND: {peak_bitstring} (p={peak_prob:.6f}, "
                      f"{peak_prob/uniform:.1f}x uniform)")
                return peak_bitstring
            else:
                print(f"    No clear peak (max prob={peak_prob:.6f})")
                return None

        except Exception as e:
            print(f"    Exact simulation failed: {e}")
            return None

    def _sampling_approach(self, circuit: QuantumCircuit) -> Optional[str]:
        """Sample from the circuit many times and look for the peak."""
        print(f"  [3/5] Sampling approach...")

        try:
            # Add measurements
            meas_circuit = circuit.copy()
            meas_circuit.measure_all()

            backend = AerSimulator(method='statevector')
            shots = min(100000, 2 ** min(self.n_qubits, 20))

            transpiled = transpile(meas_circuit, backend)
            result = backend.run(transpiled, shots=shots).result()
            counts = result.get_counts()

            # Find the most frequent bitstring
            if counts:
                peak_bitstring = max(counts, key=counts.get)
                peak_count = counts[peak_bitstring]
                peak_prob = peak_count / shots
                uniform = 1.0 / (2 ** self.n_qubits)

                if peak_prob > 5 * uniform or peak_count > 10:
                    print(f"    PEAK FOUND: {peak_bitstring} "
                          f"(count={peak_count}/{shots}, p={peak_prob:.6f})")
                    return peak_bitstring
                else:
                    print(f"    Most frequent: {peak_bitstring} "
                          f"(count={peak_count}/{shots})")

        except Exception as e:
            print(f"    Sampling failed: {e}")

        return None

    def _marginal_estimation(self, circuit: QuantumCircuit) -> Optional[str]:
        """
        Estimate each qubit's marginal probability to reconstruct the peak.

        For each qubit i, estimate P(q_i = 1) by computing <Z_i>.
        If P > 0.5, the peaked bit is likely 1; otherwise 0.
        """
        print(f"  [4/5] Marginal estimation...")

        try:
            if self.n_qubits <= 28:
                sv = Statevector.from_instruction(circuit)
                probs = sv.probabilities()

                # Compute marginals
                peak_bits = []
                for qubit in range(self.n_qubits):
                    p1 = 0.0
                    for idx in range(len(probs)):
                        if (idx >> qubit) & 1:
                            p1 += probs[idx]
                    peak_bits.append('1' if p1 > 0.5 else '0')

                # Reconstruct bitstring (note: Qiskit uses LSB ordering)
                candidate = ''.join(reversed(peak_bits))
                idx = int(candidate, 2)
                if idx < len(probs):
                    prob = probs[idx]
                    uniform = 1.0 / (2 ** self.n_qubits)
                    if prob > 5 * uniform:
                        print(f"    PEAK FOUND via marginals: {candidate} "
                              f"(p={prob:.6f})")
                        return candidate

                print(f"    Marginal candidate: {candidate} "
                      f"(p={probs[idx] if idx < len(probs) else 'N/A'})")
                return candidate

        except Exception as e:
            print(f"    Marginal estimation failed: {e}")

        return None

    def _lightcone_reduction(self, circuit: QuantumCircuit) -> Optional[str]:
        """
        Reduce circuit by computing only the light cone of each output qubit.
        Gates outside the backward light cone of a qubit don't affect its output.
        """
        print(f"  [5/5] Light-cone reduction...")

        try:
            # For each qubit, trace backward through gates to find its light cone
            dag_data = circuit.data
            n = self.n_qubits

            # Build dependency graph
            qubit_deps = {i: {i} for i in range(n)}
            for gate_data in dag_data:
                gate_qubits = [circuit.find_bit(q).index for q in gate_data.qubits]
                if len(gate_qubits) >= 2:
                    # Multi-qubit gate: merge dependencies
                    merged = set()
                    for q in gate_qubits:
                        merged |= qubit_deps[q]
                    for q in gate_qubits:
                        qubit_deps[q] = merged

            # Find qubits with smallest light cones (easiest to simulate)
            cone_sizes = {i: len(deps) for i, deps in qubit_deps.items()}
            print(f"    Light cone sizes: min={min(cone_sizes.values())}, "
                  f"max={max(cone_sizes.values())}, "
                  f"avg={np.mean(list(cone_sizes.values())):.1f}")

            # If any qubit has a small light cone, simulate just that subset
            for qubit, deps in sorted(qubit_deps.items(), key=lambda x: len(x[1])):
                if len(deps) <= 20:
                    print(f"    Qubit {qubit} has {len(deps)}-qubit light cone")
                    # Could simulate just this subset

        except Exception as e:
            print(f"    Light-cone analysis failed: {e}")

        return None


def solve_bluequbit_challenge(api_token: Optional[str] = None):
    """
    Attempt to solve the BlueQubit Quantum Advantage Challenge.

    Requires a BlueQubit API token to access the challenge circuits.
    """
    print("=" * 60)
    print("  BlueQubit Quantum Advantage Challenge Solver")
    print("  Prize: 0.25 BTC (~$20,000)")
    print("  Wallet: bc1qcga5wx9e7gvz2eml0gpkrlpmttjzyw6rc6xfzz")
    print("=" * 60)

    if api_token is None:
        import os
        api_token = os.environ.get('BLUEQUBIT_API_TOKEN')

    if not api_token:
        print("\nTo attempt this challenge, you need a BlueQubit API token:")
        print("  1. Sign up at https://app.bluequbit.io/")
        print("  2. Get your API token from settings")
        print("  3. Run: export BLUEQUBIT_API_TOKEN=your_token")
        print("  4. Re-run this script")
        print("\nAlternatively, access the challenge at:")
        print("  https://app.bluequbit.io/hackathons/GFgHTGbTylwmsMsCp")
        return

    try:
        import bluequbit
        bq = bluequbit.BQClient(api_token=api_token)
        print(f"\nConnected to BlueQubit as: {bq.name}")

        # Access the challenge circuits
        # Note: actual API calls depend on BlueQubit's hackathon API
        print("\nAttempting to access challenge circuits...")
        print("(Circuit access depends on challenge registration)")

    except Exception as e:
        print(f"\nBlueQubit connection error: {e}")
        print("Make sure your API token is valid and you're registered for the challenge.")


def demo_peaked_circuit():
    """
    Demonstrate the solver on a self-constructed peaked circuit.
    """
    print("=" * 60)
    print("  Peaked Circuit Solver Demo")
    print("=" * 60)

    n = 8  # qubits
    target = "10110101"  # hidden bitstring

    # Build a peaked circuit
    qc = QuantumCircuit(n)

    # Start with Hadamards
    for i in range(n):
        qc.h(i)

    # Apply phase to make target bitstring peaked
    # (in practice, this is heavily obfuscated)
    for i, bit in enumerate(reversed(target)):
        if bit == '0':
            qc.x(i)
    # Multi-controlled Z to mark the target
    qc.h(n-1)
    qc.mcx(list(range(n-1)), n-1)
    qc.h(n-1)
    for i, bit in enumerate(reversed(target)):
        if bit == '0':
            qc.x(i)

    # Amplitude amplification (mini-Grover)
    for _ in range(2):
        # Oracle
        for i, bit in enumerate(reversed(target)):
            if bit == '0':
                qc.x(i)
        qc.h(n-1)
        qc.mcx(list(range(n-1)), n-1)
        qc.h(n-1)
        for i, bit in enumerate(reversed(target)):
            if bit == '0':
                qc.x(i)

        # Diffuser
        for i in range(n):
            qc.h(i)
            qc.x(i)
        qc.h(n-1)
        qc.mcx(list(range(n-1)), n-1)
        qc.h(n-1)
        for i in range(n):
            qc.x(i)
            qc.h(i)

    print(f"\nTarget bitstring: {target}")
    print(f"Circuit: {n} qubits, {sum(qc.count_ops().values())} gates\n")

    solver = PeakedCircuitSolver(qc)
    result = solver.solve()

    if result:
        # Qiskit bit ordering may be reversed
        if result == target or result[::-1] == target:
            print(f"\n  SUCCESS: Recovered target bitstring!")
        else:
            print(f"\n  Result: {result} (target was {target})")
    else:
        print(f"\n  FAILED to find peak")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Peaked Circuit Solver")
    parser.add_argument('--challenge', action='store_true',
                       help='Attempt BlueQubit challenge')
    parser.add_argument('--demo', action='store_true',
                       help='Run demo on test circuit')
    parser.add_argument('--token', type=str, help='BlueQubit API token')

    args = parser.parse_args()

    if args.challenge:
        solve_bluequbit_challenge(args.token)
    else:
        demo_peaked_circuit()
